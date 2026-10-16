# Optional independent analysis using base R only.
# Rscript analyze.R reports/SmartBus_..._trips.csv analysis
# Rscript analyze.R --ridership research/cta_ridership.csv analysis/cta

fail <- function(message) stop(message, call. = FALSE)

read_input <- function(path, required, exact = FALSE) {
  if (!file.exists(path)) fail(paste("CSV not found:", path))
  d <- read.csv(path, fileEncoding = "UTF-8-BOM", colClasses = "character",
                na.strings = "", check.names = FALSE, strip.white = FALSE,
                row.names = NULL, fill = FALSE)
  if (anyDuplicated(names(d))) fail("Duplicate CSV field names are not supported.")
  missing <- setdiff(required, names(d))
  if (length(missing)) fail(paste("Missing CSV fields:", paste(missing, collapse = ", ")))
  if (exact && length(setdiff(names(d), required))) {
    fail("Ridership CSV must contain exactly date, route, daytype and rides.")
  }
  if (!nrow(d)) fail("CSV contains no records.")
  if (nrow(d) > 200000L && exact) fail("Ridership CSV exceeds the 200,000 row limit.")
  d
}

parse_dates <- function(x, field, allow_timestamp = FALSE) {
  # The provider's original CSV represents midnight dates as ISO timestamps.
  date_text <- x
  if (allow_timestamp) date_text <- sub("T00:00:00(\\.000)?$", "", date_text)
  if (anyNA(date_text) || any(!grepl("^[0-9]{4}-[0-9]{2}-[0-9]{2}$", date_text))) {
    fail(paste(field, "must use YYYY-MM-DD or an accepted midnight timestamp."))
  }
  result <- as.Date(date_text, format = "%Y-%m-%d")
  if (anyNA(result) || any(format(result, "%Y-%m-%d") != date_text)) {
    fail(paste(field, "contains an invalid calendar date."))
  }
  result
}

parse_numeric <- function(x, field, allow_blank = FALSE) {
  result <- suppressWarnings(as.numeric(x))
  invalid <- !is.na(x) & (is.na(result) | !is.finite(result))
  if (any(invalid) || (!allow_blank && anyNA(result))) {
    fail(paste(field, "contains a blank or invalid numeric value."))
  }
  result
}

write_table <- function(d, out, name) {
  write.csv(d, file.path(out, name), row.names = FALSE, na = "")
}

open_chart <- function(path) {
  if (capabilities("cairo")) {
    cairo_pdf(path, width = 11, height = 7, family = "sans")
  } else {
    pdf(path, width = 11, height = 7, family = "sans")
  }
}

analyze_trips <- function(path, out) {
  fields <- c("seats", "gross", "commission", "due", "actual", "outstanding",
              "occupancy", "capacity")
  d <- read_input(path, c("day", "route", "status", fields))
  for (field in fields) d[[field]] <- parse_numeric(d[[field]], field, field == "actual")
  d$day <- parse_dates(d$day, "day")
  if (anyNA(d$route) || any(!nzchar(trimws(d$route)))) fail("Trip route must be populated.")
  safe_sum <- function(x) if (all(is.na(x))) NA_real_ else sum(x, na.rm = TRUE)
  amounts <- c("seats", "gross", "commission", "due", "actual", "outstanding")
  daily <- aggregate(d[amounts], list(day = d$day), safe_sum)
  route <- aggregate(d[c("capacity", amounts)], list(route = d$route), safe_sum)
  route$seat_use <- ifelse(route$capacity > 0, route$seats / route$capacity, NA_real_)
  unknown <- as.integer(is.na(d$actual))
  daily$unknown_receipt_trips <- aggregate(unknown, list(day = d$day), sum)$x
  route$unknown_receipt_trips <- aggregate(unknown, list(route = d$route), sum)$x
  write_table(daily, out, "daily_summary.csv")
  write_table(route, out, "route_summary.csv")
  write_table(d[is.na(d$status) | d$status != "Matched", ], out, "trips_to_check.csv")
  open_chart(file.path(out, "route_analysis.pdf"))
  on.exit(dev.off(), add = TRUE)
  barplot(route$gross, names.arg = route$route, col = "#40566D", las = 2,
          main = "Fare by route", ylab = "Taka")
  plot(daily$day, daily$gross, type = "b", col = "#59646F",
       main = "Daily fare (recorded days)", xlab = "Date", ylab = "Taka")
  # Only read a companion counter file when the input has the export naming suffix.
  counter_path <- sub("_trips\\.csv$", "_counters.csv", path)
  if (counter_path != path && file.exists(counter_path)) {
    c <- read_input(counter_path, c("counter", amounts))
    if (anyNA(c$counter)) fail("Counter name must be populated.")
    for (field in amounts) c[[field]] <- parse_numeric(c[[field]], field, field == "actual")
    counter <- aggregate(c[amounts], list(counter = c$counter), safe_sum)
    write_table(counter, out, "counter_summary.csv")
  }
  cat("Trip analysis saved to", out, "\n")
}

analyze_ridership <- function(path, out) {
  d <- read_input(path, c("date", "route", "daytype", "rides"), exact = TRUE)
  d$date <- parse_dates(d$date, "date", allow_timestamp = TRUE)
  if (anyNA(d$route) || any(!nzchar(d$route)) || any(nchar(d$route) > 80L) ||
      any(d$route != trimws(d$route)) ||
      any(grepl("[[:cntrl:]]", d$route))) {
    fail("route must be a nonblank, unpadded text identifier without control characters.")
  }
  if (anyNA(d$daytype) || any(!d$daytype %in% c("W", "A", "U"))) {
    fail("daytype must be W (weekday), A (Saturday), or U (Sunday/holiday).")
  }
  if (anyNA(d$rides) || any(!grepl("^[0-9]+$", d$rides))) {
    fail("rides must be a nonnegative whole number with no blanks.")
  }
  d$rides <- parse_numeric(d$rides, "rides")
  if (any(d$rides > 1000000000)) fail("rides exceeds the supported 1,000,000,000 per-record limit.")
  if (anyDuplicated(d[c("date", "route")])) fail("Duplicate date/route records are not supported.")
  d <- d[order(d$date, d$route), ]
  dates <- sort(unique(d$date))
  if (length(dates) < 14L) fail("At least 14 distinct observed dates are required for a 7-date holdout.")
  if (as.numeric(max(dates) - min(dates)) >= 366) fail("Choose a data range of at most 366 days.")

  daily <- aggregate(d["rides"], list(date = d$date), sum)
  daily$routes_observed <- aggregate(d$route, list(date = d$date), length)$x
  daily <- daily[order(daily$date), ]
  route_sum <- aggregate(d["rides"], list(route = d$route), sum)
  names(route_sum)[2] <- "total_observed_rides"
  route_sum$recorded_days <- aggregate(d$rides, list(route = d$route), length)$x
  route_sum$mean_recorded_daily_rides <- aggregate(d$rides, list(route = d$route), mean)$x
  route_sum <- route_sum[order(-route_sum$total_observed_rides, route_sum$route), ]
  # Calendar weekday remains distinct from the provider's Sunday/holiday daytype.
  weekday_number <- as.POSIXlt(d$date, tz = "UTC")$wday
  weekday <- aggregate(d["rides"], list(weekday_number = weekday_number), sum)
  weekday$records <- aggregate(d$rides, list(weekday_number = weekday_number), length)$x
  weekday$mean_route_day_rides <- weekday$rides / weekday$records
  weekday$weekday <- c("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")[weekday$weekday_number + 1L]
  daytype <- aggregate(d["rides"], list(daytype = d$daytype), sum)
  daytype$records <- aggregate(d$rides, list(daytype = d$daytype), length)$x
  daytype$mean_route_day_rides <- daytype$rides / daytype$records

  cutoff <- dates[length(dates) - 6L]
  train <- d[d$date < cutoff, ]
  held <- d[d$date >= cutoff, ]
  historical <- aggregate(train["rides"], list(route = train$route, daytype = train$daytype), mean)
  # Match two columns without concatenated keys: route identifiers may contain separators.
  held$predicted <- vapply(seq_len(nrow(held)), function(i) {
    values <- historical$rides[historical$route == held$route[i] & historical$daytype == held$daytype[i]]
    if (length(values)) values[1] else NA_real_
  }, numeric(1))
  last <- train[!duplicated(train$route, fromLast = TRUE), ]
  held$baseline <- last$rides[match(held$route, last$route)]
  held$eligible_for_comparison <- !is.na(held$predicted) & !is.na(held$baseline)
  held$exclusion_reason <- ifelse(held$eligible_for_comparison, "",
                                 ifelse(is.na(held$baseline), "Unseen route in training",
                                        "Unseen route/daytype in training"))
  held$absolute_error <- abs(held$rides - held$predicted)
  held$baseline_absolute_error <- abs(held$rides - held$baseline)
  eligible <- held[held$eligible_for_comparison, ]
  if (!nrow(eligible)) fail("No holdout records have both route/daytype and route baseline training history.")
  mae <- function(prediction) if (nrow(eligible)) mean(abs(eligible$rides - prediction)) else NA_real_
  metrics <- data.frame(
    model = c("Historical route/daytype mean", "Last observed training value by route"),
    mae_rides = c(mae(eligible$predicted), mae(eligible$baseline)),
    evaluated_route_days = rep(nrow(eligible), 2),
    excluded_route_days = rep(nrow(held) - nrow(eligible), 2),
    training_start = rep(as.character(min(train$date)), 2),
    training_end = rep(as.character(max(train$date)), 2),
    holdout_start = rep(as.character(min(held$date)), 2),
    holdout_end = rep(as.character(max(held$date)), 2)
  )
  write_table(daily, out, "ridership_daily_summary.csv")
  write_table(route_sum, out, "ridership_route_summary.csv")
  write_table(weekday, out, "ridership_weekday_summary.csv")
  write_table(daytype, out, "ridership_daytype_summary.csv")
  write_table(held, out, "ridership_holdout_predictions.csv")
  write_table(metrics, out, "ridership_forecast_metrics.csv")
  writeLines(c(
    "Public ridership analysis; independent of SmartBus financial demo accounts.",
    paste("Observed data:", min(d$date), "to", max(d$date)),
    paste("Training ends:", max(train$date), "; holdout begins:", min(held$date)),
    "The holdout is the last 7 distinct observed dates; missing dates are not filled with zeros.",
    "Both forecasts are fixed at the training cutoff and never read holdout outcomes.",
    "Mean forecast: arithmetic historical mean for the same route and provider daytype.",
    "Baseline: last observed training rides for the route, irrespective of daytype.",
    "MAE is compared on the same eligible route/date records; see exclusions in predictions.",
    "MAE unit is rides per route/day. No MAPE is reported, avoiding division by zero.",
    "Weekday means are route-day means over observed records, not system-wide daily means.",
    "Counts are boardings/rides, not unique people, occupancy, seats, fares or receipts.",
    "One short, fixed holdout is descriptive evidence, not proof of future forecast accuracy.",
    "See research/source.json for source attribution and retrieval details."
  ), file.path(out, "ridership_methodology.txt"))
  open_chart(file.path(out, "ridership_analysis.pdf"))
  on.exit(dev.off(), add = TRUE)
  plot(daily$date, daily$rides, type = "l", col = "#22675F", lwd = 2,
       main = "CTA public ridership (observed records)", xlab = "Date", ylab = "Rides")
  abline(v = as.numeric(cutoff), col = "#A65E2E", lty = 2)
  legend("topright", legend = "Holdout starts", col = "#A65E2E", lty = 2, bty = "n")
  top <- head(route_sum, 12L)
  barplot(top$total_observed_rides, names.arg = top$route, las = 2, col = "#40566D",
          main = "Top observed routes in this extract", xlab = "CTA route", ylab = "Observed rides")
  cat("Ridership analysis saved to", out, "\n")
  print(metrics, row.names = FALSE)
}

args <- commandArgs(trailingOnly = TRUE)
if (!length(args) || args[1] %in% c("--help", "-h")) {
  cat("Usage:\n  Rscript analyze.R <trips.csv> [outdir]\n",
      "  Rscript analyze.R --ridership <ridership.csv> [outdir]\n", sep = "")
  if (!length(args)) quit(status = 1)
} else if (args[1] == "--ridership") {
  if (length(args) < 2L || length(args) > 3L) fail("Choose a ridership CSV and optional output folder.")
  out <- if (length(args) == 3L) args[3] else "analysis/cta"
  dir.create(out, recursive = TRUE, showWarnings = FALSE)
  analyze_ridership(args[2], out)
} else {
  if (length(args) > 2L) fail("Choose a trips CSV and optional output folder.")
  out <- if (length(args) == 2L) args[2] else "analysis"
  dir.create(out, recursive = TRUE, showWarnings = FALSE)
  analyze_trips(args[1], out)
}
