import pandas as pd
import numpy as np
from datetime import datetime

# Initial parameters
chris_age_2026 = 60
mandy_age_2026 = 62
chris_life_expectancy = 95
mandy_life_expectancy = 85

initial_ira = 2_300_000
annual_spending_need = 100_000
investment_return = 0.07
inflation_rate = 0.03

chris_ss_annual = 3_500 * 12
mandy_ss_annual = 2_000 * 12
ss_start_age_chris = 67
ss_start_age_mandy = 67

# 2026 Tax brackets (MFJ) - assuming TCJA provisions extended or similar
# Standard deduction for 65+ in 2026 (estimated)
standard_deduction_2026 = 32_300  # Base + age 65+ addition

# Tax brackets for 2026 (estimated based on inflation adjustments)
tax_brackets_2026 = [
    (0, 23_200, 0.10),
    (23_200, 94_300, 0.12),
    (94_300, 201_050, 0.22),
    (201_050, 383_900, 0.24),
    (383_900, 487_450, 0.32),
    (487_450, 731_200, 0.35),
    (731_200, float('inf'), 0.37)
]

# RMD divisors (Uniform Lifetime Table)
rmd_table = {
    73: 26.5, 74: 25.5, 75: 24.6, 76: 23.7, 77: 22.9, 78: 22.0, 79: 21.1,
    80: 20.2, 81: 19.4, 82: 18.5, 83: 17.7, 84: 16.8, 85: 16.0, 86: 15.2,
    87: 14.4, 88: 13.7, 89: 12.9, 90: 12.2, 91: 11.5, 92: 10.8, 93: 10.1,
    94: 9.5, 95: 8.9
}

def calculate_federal_tax(taxable_income, brackets):
    """Calculate federal income tax"""
    tax = 0
    for i, (lower, upper, rate) in enumerate(brackets):
        if taxable_income > lower:
            taxable_in_bracket = min(taxable_income, upper) - lower
            tax += taxable_in_bracket * rate
        if taxable_income <= upper:
            break
    return tax

def calculate_ss_taxable(ss_benefit, agi):
    """Calculate taxable portion of Social Security"""
    if ss_benefit == 0:
        return 0
    
    provisional_income = agi + (ss_benefit * 0.5)
    
    # MFJ thresholds
    threshold1 = 32_000
    threshold2 = 44_000
    
    if provisional_income <= threshold1:
        return 0
    elif provisional_income <= threshold2:
        return min(ss_benefit * 0.5, (provisional_income - threshold1) * 0.5)
    else:
        amount1 = min(ss_benefit * 0.5, (threshold2 - threshold1) * 0.5)
        amount2 = min(ss_benefit * 0.85 - amount1, (provisional_income - threshold2) * 0.85)
        return amount1 + amount2

def run_scenario(scenario_name, do_conversions=False):
    """Run retirement scenario with or without Roth conversions"""
    
    results = []
    
    # Initialize balances
    trad_ira = initial_ira
    roth_ira = 0
    
    year = 2026
    chris_age = chris_age_2026
    mandy_age = mandy_age_2026
    
    while chris_age <= chris_life_expectancy or mandy_age <= mandy_life_expectancy:
        year_data = {
            'Year': year,
            'Chris_Age': chris_age,
            'Mandy_Age': mandy_age,
            'Scenario': scenario_name
        }
        
        # Determine if still alive
        chris_alive = chris_age <= chris_life_expectancy
        mandy_alive = mandy_age <= mandy_life_expectancy
        both_alive = chris_alive and mandy_alive
        
        # Beginning balances
        year_data['Trad_IRA_Begin'] = trad_ira
        year_data['Roth_IRA_Begin'] = roth_ira
        
        # Social Security
        chris_ss = chris_ss_annual if chris_age >= ss_start_age_chris and chris_alive else 0
        mandy_ss = mandy_ss_annual if mandy_age >= ss_start_age_mandy and mandy_alive else 0
        total_ss = chris_ss + mandy_ss
        year_data['Social_Security'] = total_ss
        
        # RMD calculation
        rmd_age = max(chris_age if chris_alive else 0, mandy_age if mandy_alive else 0)
        if rmd_age >= 73 and trad_ira > 0:
            rmd = trad_ira / rmd_table.get(rmd_age, 8.9)
        else:
            rmd = 0
        year_data['RMD'] = rmd
        
        # Spending need (inflated) - calculate this early as it's needed for conversion sizing
        years_since_2026 = year - 2026
        spending_need = annual_spending_need * ((1 + inflation_rate) ** years_since_2026)
        year_data['Spending_Need'] = spending_need
        
        # Roth conversion
        conversion = 0
        if do_conversions and chris_age < 73:  # Convert before RMDs start
            # Calculate max we can withdraw to stay at top of 24% bracket
            std_deduction = standard_deduction_2026 if both_alive else standard_deduction_2026 * 0.7
            top_of_24_bracket = 383_900
            
            # Work backwards from taxable income to total withdrawal
            # Taxable income = AGI + Taxable SS - Std Deduction
            # We want: Taxable income = 383,900
            # So: AGI + Taxable SS = 383,900 + 32,300 = 416,200
            
            # For simplicity, ignore taxable SS for now (it's 0 until age 67 anyway)
            # AGI = Total Withdrawal (RMD + Conversion + Additional)
            target_agi = top_of_24_bracket + std_deduction
            
            # Calculate tax on this AGI
            taxable_ss = calculate_ss_taxable(total_ss, target_agi)
            taxable_income = max(0, target_agi + taxable_ss - std_deduction)
            tax_at_max = calculate_federal_tax(taxable_income, tax_brackets_2026)
            
            # Total cash needed = spending + tax
            total_cash_needed = spending_need + tax_at_max
            
            # Cash available from other sources
            cash_from_other = total_ss + rmd
            
            # Additional withdrawal needed for spending/taxes
            additional_for_spending = max(0, total_cash_needed - cash_from_other)
            
            # Total withdrawal = RMD + Additional + Conversion
            # We want total withdrawal = target_agi
            # So: Conversion = target_agi - RMD - Additional
            max_conversion = target_agi - rmd - additional_for_spending
            
            # Can't convert more than we have
            conversion = min(max_conversion, trad_ira)
            conversion = max(0, conversion)
        
        year_data['Roth_Conversion'] = conversion
        
        # Total withdrawals from traditional IRA (will be recalculated with additional)
        
        # Standard deduction
        std_deduction = standard_deduction_2026 if both_alive else standard_deduction_2026 * 0.7
        
        # Now we need to solve for additional withdrawal iteratively
        # because additional withdrawal increases AGI, which increases tax, which increases withdrawal needed
        # Start with initial estimate based on conversion + RMD
        additional_withdrawal = 0
        
        for iteration in range(10):  # Should converge quickly
            # Total traditional IRA withdrawal
            total_trad_withdrawal = rmd + conversion + additional_withdrawal
            
            # AGI calculation
            agi = total_trad_withdrawal
            taxable_ss = calculate_ss_taxable(total_ss, agi)
            
            # Taxable income
            taxable_income = max(0, agi + taxable_ss - std_deduction)
            
            # Federal tax
            federal_tax = calculate_federal_tax(taxable_income, tax_brackets_2026)
            
            # Cash needs: Spending + Tax
            # Cash sources: SS + RMD + Additional (conversion goes to Roth, not available for spending)
            total_cash_needed = spending_need + federal_tax
            cash_from_ss_and_rmd = total_ss + rmd
            
            # Calculate new additional withdrawal needed
            new_additional = max(0, total_cash_needed - cash_from_ss_and_rmd)
            
            # Check convergence
            if abs(new_additional - additional_withdrawal) < 1:
                additional_withdrawal = new_additional
                break
            
            additional_withdrawal = new_additional
        
        # Store final values
        year_data['Additional_Withdrawal'] = additional_withdrawal
        year_data['Taxable_SS'] = taxable_ss
        year_data['Taxable_Income'] = taxable_income
        year_data['Federal_Tax'] = federal_tax
        
        # Total IRA distribution (all coming out of traditional IRA)
        # This includes: RMD (for spending/taxes) + Conversion (to Roth) + Additional (for spending/taxes)
        total_ira_distribution = rmd + conversion + additional_withdrawal
        year_data['Total_IRA_Distribution'] = total_ira_distribution
        
        # Update balances
        # Traditional IRA: 
        # - Starts with beginning balance
        # - Grows at 7% during the year
        # - Distributions taken at end of year (simplified assumption)
        # More accurate: assume distributions taken mid-year, so average balance earns return
        
        # For simplicity, let's assume beginning balance grows all year, then distributions taken at end
        trad_ira_after_growth = trad_ira * (1 + investment_return)
        trad_ira = max(0, trad_ira_after_growth - total_ira_distribution)
        
        # Roth IRA: add conversions at beginning of year, then entire balance grows
        # This is conservative (assumes conversion happens at year start)
        roth_ira = (roth_ira + conversion) * (1 + investment_return)
        
        year_data['Trad_IRA_End'] = trad_ira
        year_data['Roth_IRA_End'] = roth_ira
        year_data['Total_Assets_End'] = trad_ira + roth_ira
        
        # Net spending (what they actually get to spend after taxes)
        net_available = total_ss + total_ira_distribution - federal_tax
        year_data['Net_Available'] = net_available
        year_data['Surplus_Deficit'] = net_available - spending_need
        
        results.append(year_data)
        
        year += 1
        chris_age += 1
        mandy_age += 1
    
    return pd.DataFrame(results)

# Run both scenarios
print("Running baseline scenario (no conversions)...")
baseline_df = run_scenario("Baseline", do_conversions=False)

print("Running conversion scenario (maximize 24% bracket)...")
conversion_df = run_scenario("With_Conversions", do_conversions=True)

# Combine for comparison
combined_df = pd.concat([baseline_df, conversion_df], ignore_index=True)

# Save to Excel with multiple sheets
output_file = '/mnt/user-data/outputs/roth_conversion_analysis.xlsx'

with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    # Baseline scenario
    baseline_df.to_excel(writer, sheet_name='Baseline_No_Conversions', index=False)
    
    # Conversion scenario
    conversion_df.to_excel(writer, sheet_name='With_Conversions', index=False)
    
    # Summary comparison
    summary_data = []
    
    for scenario, df in [('Baseline', baseline_df), ('With Conversions', conversion_df)]:
        total_taxes = df['Federal_Tax'].sum()
        total_conversions = df['Roth_Conversion'].sum()
        final_trad = df['Trad_IRA_End'].iloc[-1]
        final_roth = df['Roth_IRA_End'].iloc[-1]
        total_assets = final_trad + final_roth
        avg_surplus = df['Surplus_Deficit'].mean()
        
        summary_data.append({
            'Scenario': scenario,
            'Total_Lifetime_Taxes': total_taxes,
            'Total_Conversions': total_conversions,
            'Final_Traditional_IRA': final_trad,
            'Final_Roth_IRA': final_roth,
            'Total_Final_Assets': total_assets,
            'Avg_Annual_Surplus': avg_surplus
        })
    
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_excel(writer, sheet_name='Summary_Comparison', index=False)
    
    # Conversion years detail (first 10 years showing conversion activity)
    conversion_years = conversion_df[conversion_df['Roth_Conversion'] > 0].head(15)
    if len(conversion_years) > 0:
        conversion_years.to_excel(writer, sheet_name='Conversion_Years_Detail', index=False)

print(f"\nAnalysis complete! File saved to: {output_file}")
print("\n" + "="*80)
print("SUMMARY COMPARISON")
print("="*80)

for scenario, df in [('Baseline (No Conversions)', baseline_df), ('With Roth Conversions', conversion_df)]:
    print(f"\n{scenario}:")
    print(f"  Total Lifetime Federal Taxes: ${df['Federal_Tax'].sum():,.0f}")
    print(f"  Total Roth Conversions: ${df['Roth_Conversion'].sum():,.0f}")
    print(f"  Final Traditional IRA: ${df['Trad_IRA_End'].iloc[-1]:,.0f}")
    print(f"  Final Roth IRA: ${df['Roth_IRA_End'].iloc[-1]:,.0f}")
    print(f"  Total Final Assets: ${(df['Trad_IRA_End'].iloc[-1] + df['Roth_IRA_End'].iloc[-1]):,.0f}")
    print(f"  Average Annual Surplus/Deficit: ${df['Surplus_Deficit'].mean():,.0f}")

print("\n" + "="*80)
