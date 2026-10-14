import unittest,tempfile,shutil,copy
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from datetime import date,datetime,timedelta
from unittest.mock import patch
import xml.etree.ElementTree as E
import daily_system as d
from report_layout import summary

def change(path,updates):
 with ZipFile(path) as z:files={n:z.read(n) for n in z.namelist()}
 parts=d.workbook_parts(files)
 for name,values in updates.items():
  tree=E.fromstring(files[parts[name]])
  for ref,val in values.items():d.set_cell(tree,ref,val)
  files[parts[name]]=E.tostring(tree,encoding='utf-8',xml_declaration=True)
 with ZipFile(path,'w',ZIP_DEFLATED) as z:
  for n,raw in files.items():z.writestr(n,raw)
class ExcelTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.folder=Path(self.tmp.name);self.path=self.folder/'Daily_2026-10-12_en.xlsx';shutil.copy2(d.ROOT/'Demo_2026-10-12_en.xlsx',self.path);change(self.path,{'Settings':{'B9':'LIVE'}})
 def tearDown(self):self.tmp.cleanup()
 def test_new_columns_and_finances(self):
  b=d.calculate(self.path);_,s=summary([b]);self.assertEqual((s['gross'],s['commission'],s['due'],s['actual'],s['outstanding']),(70600,2250,68350,49450,18900));self.assertEqual(b['trips'][0]['capacity'],62);self.assertEqual(b['trips'][0]['driver_phone'],'01000000100')
  raw=d.read_book(self.path);
  with ZipFile(self.path) as z:
   sheet=E.fromstring(z.read('xl/worksheets/sheet1.xml'));self.assertEqual(sheet.find(".//s:c[@r='F5']/s:v",d.NS).text,'3')
  self.assertEqual(raw['Trips']['T5'],'Seat use');self.assertNotIn('U5',raw['Trips']);self.assertNotIn('O5',raw['Collections']);self.assertEqual(raw['Collections']['F5'],'Counter type');self.assertNotIn('C5',raw['Counters'])
 def test_separate_counter_shortfall_and_overpayment(self):
  change(self.path,{'Collections':{'M6':3100}});t=d.calculate(self.path)['trips'][0];self.assertEqual((t['outstanding'],t['extra_received']),(300,400))
 def test_multiple_counter_lines_one_deposit(self):
  change(self.path,{'Collections':{'D12':'218','E12':'Gabtoli AC','G12':1}});b=d.calculate(self.path);g=next(g for g in b['counter_groups'] if g['trip']=='218' and g['counter']=='Gabtoli AC');self.assertEqual((g['seats'],g['due'],g['actual'],g['outstanding']),(4,3600,2600,1000))
 def test_zero_missing_and_capacity(self):
  self.assertEqual(d.calculate(self.path)['trips'][1]['status'],'Deposit pending');change(self.path,{'Collections':{'M10':0,'G7':80}});b=d.calculate(self.path);self.assertEqual(b['trips'][1]['status'],'Short / extra');self.assertIn('Sold seats exceed bus capacity',b['trips'][0]['issues'])
 def test_daily_creation_carries_lists_without_transactions(self):
  p=d.create_daily('2026-10-13',folder=self.folder);b=d.calculate(p);self.assertEqual(b['trips'],[]);self.assertEqual(len(b['buses']),3);raw=d.read_book(p);self.assertEqual(raw['Buses']['B6'],'Demo Driver 1');self.assertNotIn('D5',raw['Crew']);self.assertEqual(raw['Counters']['B6'],'Own')
 def test_english_defaults_and_report_text(self):
  p=d.create_daily('2026-10-13',folder=self.folder);self.assertEqual(p.name,'Daily_2026-10-13_en.xlsx');self.assertEqual(d.read_book(p)['Settings']['B11'],'en')
  html=d.report_html([d.calculate(self.path)],[],[],'2026-10-12','2026-10-12');self.assertIn('<html lang="en">',html);self.assertIn('Dashboard',html);self.assertIn('68,350.00',html);self.assertNotRegex(html,r'[\u0980-\u09ff]')
 def test_packaged_workbook_strings_are_english(self):
  paths=sorted(d.ROOT.rglob('*_en.xlsx'));self.assertTrue(paths);self.assertTrue((d.ROOT/'Daily_Template_en.xlsx').is_file());self.assertTrue((d.ROOT/'Demo_2026-10-12_en.xlsx').is_file())
  for path in paths:
   with self.subTest(workbook=path.name),ZipFile(path) as archive:
    for name in archive.namelist():
     if not name.endswith('.xml'):continue
     tree=E.fromstring(archive.read(name))
     for node in tree.iter():
      self.assertNotRegex(node.text or '',r'[\u0980-\u09ff]',msg=f'{path.name}: {name}')
      self.assertNotRegex(node.tail or '',r'[\u0980-\u09ff]',msg=f'{path.name}: {name}')
      for attribute in node.attrib.values():self.assertNotRegex(attribute,r'[\u0980-\u09ff]',msg=f'{path.name}: {name}')
 def test_non_english_output_requests_are_rejected(self):
  from period_export import build_cells,make_period_excel
  book=d.calculate(self.path)
  requests=[lambda:d.create_daily('2026-10-13','bn',self.folder),lambda:d.report_html([book],[],[],'2026-10-12','2026-10-12','bn'),lambda:d.make_report(self.folder,'2026-10-12','2026-10-12','bn'),lambda:build_cells([book],'2026-10-12','2026-10-12','bn'),lambda:make_period_excel(self.folder,'2026-10-12','2026-10-12','bn')]
  for request in requests:
   with self.subTest(request=request),self.assertRaisesRegex(ValueError,'English'):request()
 def test_year_snapshot_and_pdf(self):
  from period_export import make_period_excel
  base=d.calculate(self.path);books=[]
  for i in range(365):
   b=copy.deepcopy(base);day=date(2026,1,1)+timedelta(days=i);b['day']=str(day)
   for t in b['trips']:t['day']=str(day);t['start']=datetime.combine(day,t['start'].time())
   books.append(b)
  with patch('daily_system.collect',return_value=(books,[],[])):p=make_period_excel(self.folder,'2026-01-01','2026-12-31',report_folder=self.folder)
  raw=d.read_book(p);self.assertEqual(raw['Dashboard']['F5'],1095);self.assertEqual(raw['Dashboard']['F8'],70600*365);self.assertEqual(raw['Collections']['D2195'],'220');self.assertIn('A1100',raw['Trips'])
  html=d.report_html([base],[],[],'2026-10-12','2026-10-12');self.assertIn('Dashboard',html);self.assertIn('68,350.00',html);self.assertNotRegex(html,r'[\u0980-\u09ff]')
 def test_structure_freeze_and_charts(self):
  with ZipFile(d.ROOT/'Demo_2026-10-12_en.xlsx') as z:
   names=[s.get('name') for s in E.fromstring(z.read('xl/workbook.xml')).findall('s:sheets/s:sheet',d.NS)];self.assertEqual(names,['Dashboard','Trips','Collections','Buses','Crew','Counters','Routes','Route List','Settings','Read the Manual'])
   pane=E.fromstring(z.read('xl/worksheets/sheet2.xml')).find('.//s:pane',d.NS);self.assertEqual(pane.get('xSplit'),'3');self.assertEqual(pane.get('topLeftCell'),'D6');self.assertEqual(len([n for n in z.namelist() if '/charts/chart' in n and n.endswith('.xml')]),2)
 def test_automatic_ids_routes_and_drivers(self):
  b=d.calculate(self.path);self.assertEqual([t['trip'] for t in b['trips']],['218','219','220']);self.assertEqual(b['trips'][0]['coach'],701);self.assertEqual(b['trips'][1]['route'],'Chattogram - Dhaka')
  change(self.path,{'Trips':{'B9':703,'C9':46207.5,'E9':'Going','F9':'Demo Bus 1'}})
  b=d.calculate(self.path);self.assertEqual(b['trips'][3]['trip'],'221');self.assertEqual(b['trips'][3]['driver'],'Demo Driver 1');self.assertEqual(b['trips'][3]['capacity'],62)
 def test_route_price_updates_from_master(self):
  change(self.path,{'Route List':{'G6':950}});b=d.calculate(self.path);t=b['trips'][0];self.assertEqual(t['gross'],13300);self.assertEqual(t['commission'],250)
 def test_missing_rate_and_manual_sold_seats(self):
  change(self.path,{'Route List':{'G6':None},'Trips':{'N6':1}});b=d.calculate(self.path);self.assertTrue(any('Invalid ticket fare' in x for x in b['trips'][0]['issues']));self.assertTrue(any('sold seats' in x for x in b['trips'][0]['issues']))

if __name__=='__main__':unittest.main()
