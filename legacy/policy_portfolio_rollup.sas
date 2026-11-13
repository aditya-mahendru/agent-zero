/* policy_portfolio_rollup.sas
   Business purpose: portfolio rollup of sum insured and policy count by
   region and product line, with a BY-group subtotal per region -- feeds
   the quarterly portfolio exposure report sent to reinsurers.
   Legacy quirks: PROC MEANS for the aggregate, a DATA step BY-group pass
   for region-level subtotal lines inserted into the output (a reporting
   convention this insurer still uses), missing-region handling. */

libname src "/legacy_data";
libname out "/legacy_data_out";

data policies_clean;
    set src.policies;
    if region = "" then
        region = "UNKNOWN";
run;

proc sort data=policies_clean out=policies_sorted;
    by region product_line;
run;

proc means data=policies_sorted noprint nway;
    class region product_line;
    var sum_insured;
    output out=portfolio_agg (drop=_type_ _freq_)
        sum=total_sum_insured
        n=policy_count;
run;

proc sort data=portfolio_agg out=portfolio_agg_sorted;
    by region product_line;
run;

/* Insert a subtotal row after the last product_line within each region --
   a reporting convention carried over from the original paper-report era. */
data policy_portfolio_rollup;
    set portfolio_agg_sorted;
    by region;
    retain region_total_sum_insured region_total_policy_count 0;

    if first.region then do;
        region_total_sum_insured = 0;
        region_total_policy_count = 0;
    end;

    region_total_sum_insured + total_sum_insured;
    region_total_policy_count + policy_count;

    output;

    if last.region then do;
        product_line = "ALL";
        total_sum_insured = region_total_sum_insured;
        policy_count = region_total_policy_count;
        output;
    end;
run;

proc sort data=policy_portfolio_rollup out=out.policy_portfolio_rollup;
    by region product_line;
run;
