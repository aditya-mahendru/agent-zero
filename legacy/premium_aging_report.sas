/* premium_aging_report.sas
   Business purpose: ageing of premium collection delay, bucketed, with a
   running total of overdue premium amount kept per product line -- feeds
   the collections team's weekly report.
   Legacy quirks: DATA step date arithmetic, nested IF-THEN/ELSE bucketing,
   BY-group RETAIN running total (reset at each BY-group boundary), FORMAT
   for report-ready output. */

libname src "/legacy_data";
libname out "/legacy_data_out";

proc sort data=src.premiums out=premiums_sorted;
    by policy_id;
run;

proc sort data=src.policies out=policies_sorted;
    by policy_id;
run;

data premium_with_product;
    merge premiums_sorted (in=in_prem)
          policies_sorted (keep=policy_id product_line region in=in_pol);
    by policy_id;
    if in_prem and in_pol;
run;

proc sort data=premium_with_product out=premium_sorted_by_product;
    by product_line policy_id;
run;

data premium_aging_report;
    set premium_sorted_by_product;
    by product_line;

    format collection_delay_days 8.
           aging_bucket $10.
           running_overdue_total 12.2;

    collection_delay_days = collected_date - period_start;

    if collection_delay_days <= 0 then
        aging_bucket = "On Time";
    else if collection_delay_days <= 30 then
        aging_bucket = "1-30 Days";
    else if collection_delay_days <= 60 then
        aging_bucket = "31-60 Days";
    else
        aging_bucket = "60+ Days";

    /* Running total of overdue premium resets at the start of each
       product_line BY-group. */
    if first.product_line then
        running_overdue_total = 0;

    if aging_bucket ne "On Time" then
        running_overdue_total + premium_amount;
run;

proc sort data=premium_aging_report out=out.premium_aging_report;
    by product_line policy_id;
run;
