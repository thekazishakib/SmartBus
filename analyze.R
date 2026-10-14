# Optional R analysis of a period's trips CSV. Base R with Cairo and system fonts.
# Rscript analyze.R reports/SmartBus_..._trips.csv analysis
args <- commandArgs(trailingOnly=TRUE)
if(length(args)<1) stop("Choose the trips CSV saved with the PDF.")
out <- if(length(args)>1) args[2] else "analysis"
dir.create(out,recursive=TRUE,showWarnings=FALSE)
d <- read.csv(args[1],fileEncoding="UTF-8-BOM",colClasses="character",na.strings="")
if(nrow(d)==0) stop("No trips found")
fields <- c("seats","gross","commission","due","actual","outstanding","occupancy","capacity")
for(k in fields)d[[k]] <- as.numeric(d[[k]])
d$day <- as.Date(d$day)
safe_sum <- function(x) if(all(is.na(x))) NA_real_ else sum(x,na.rm=TRUE)
daily <- aggregate(d[c("seats","gross","commission","due","actual","outstanding")],list(day=d$day),safe_sum)
route <- aggregate(d[c("seats","capacity","gross","commission","due","actual","outstanding")],list(route=d$route),safe_sum)
route$seat_use <- route$seats/route$capacity
write.csv(daily,file.path(out,"daily_summary.csv"),row.names=FALSE,na="")
write.csv(route,file.path(out,"route_summary.csv"),row.names=FALSE,na="")
write.csv(d[d$status!="Matched",],file.path(out,"trips_to_check.csv"),row.names=FALSE,na="")
cairo_pdf(file.path(out,"route_analysis.pdf"),width=11,height=7,family="sans")
barplot(route$gross,names.arg=route$route,col="#40566D",las=2,main="Fare by route",ylab="Taka")
plot(daily$day,daily$gross,type="b",col="#59646F",main="Daily fare (recorded days)",xlab="Date",ylab="Taka")
dev.off()
counter_path <- sub("_trips.csv$","_counters.csv",args[1])
if(file.exists(counter_path)){
 c <- read.csv(counter_path,fileEncoding="UTF-8-BOM",colClasses="character",na.strings="")
 money_fields <- c("seats","gross","commission","due","actual","outstanding")
 for(k in money_fields)c[[k]] <- as.numeric(c[[k]])
 counter <- aggregate(c[money_fields],list(counter=c$counter),safe_sum)
 write.csv(counter,file.path(out,"counter_summary.csv"),row.names=FALSE,na="")
}
cat("Saved analysis to",out,"\n")
