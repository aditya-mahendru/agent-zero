/* claims_summary.sas
   Business purpose: per-policy claims summary (count, total paid, max
   single claim) joined back to policy attributes, for the actuarial
   claims review pack.
   Legacy quirks: PROC SQL join + GROUP BY, a DATA step merge with
   BY-group processing (requires both inputs pre-sorted by policy_id),
   IF-THEN/ELSE recoding, RETAIN for a running flag across the BY group. */

libname src "/legacy_data";
libname out "/legacy_data_out";

proc sort data=src.policies out=policies_sorted;
    by policy_id;
run;

proc sort data=src.claims out=claims_sorted;
    by policy_id;
run;

/* Per-policy claim aggregates via PROC SQL (legacy jobs mix PROC SQL and
   DATA step freely -- preserved here deliberately). */
proc sql;
    create table claims_agg as
    select
        policy_id,
        count(*)            as claim_count,
        sum(claim_amount)   as total_claim_amount,
        max(claim_amount)   as max_claim_amount
    from claims_sorted
    group by policy_id;
quit;

proc sort data=claims_agg out=claims_agg_sorted;
    by policy_id;
run;

/* BY-group merge: for every policy, attach its claim aggregate (if any)
   and recompute a loss severity flag. RETAIN keeps the running
   high-severity policy count across the whole BY group traversal. */
data claims_summary;
    merge policies_sorted (in=in_pol)
          claims_agg_sorted (in=in_claims);
    by policy_id;
    retain high_severity_count 0;

    if in_claims then do;
        claim_count = claim_count;
        total_claim_amount = total_claim_amount;
        max_claim_amount = max_claim_amount;
    end;
    else do;
        claim_count = 0;
        total_claim_amount = 0;
        max_claim_amount = 0;
    end;

    if sum_insured > 0 then
        severity_ratio = max_claim_amount / sum_insured;
    else
        severity_ratio = 0;

    if severity_ratio >= 0.5 then do;
        severity_flag = "HIGH";
        high_severity_count + 1;
    end;
    else if severity_ratio >= 0.25 then
        severity_flag = "MEDIUM";
    else
        severity_flag = "LOW";

    if in_pol;
    drop in_pol in_claims;
run;

proc sort data=claims_summary out=out.claims_summary;
    by product_line policy_id;
run;
