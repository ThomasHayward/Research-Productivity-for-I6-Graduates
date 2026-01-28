"""
Analysis of publication rates (publications per year) post-residency
Controls for time since graduation by using rates instead of raw counts
"""

import os
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
from scipy import stats
from util.effect_size import print_cohens_d
from util.mannwhitney import print_mannwhitney
from util.odds_ratio import print_odds_ratio
from util.robust_stats import print_median_iqr, print_prop_above_threshold
from util.ttest import print_ttest_summary, print_welchs_ttest


def analyze_publication_rates(csv_file, output_dir):
    """
    Analyze publication rates (pubs/year) controlling for time since graduation
    
    Args:
        csv_file: CSV file with publication rate data from SQL query
        output_dir: Directory to save analysis outputs
    """
    
    # Load data
    df = pd.read_csv(csv_file)
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Create output files
    stats_file = os.path.join(output_dir, 'publication_rates_analysis.txt')
    
    with open(stats_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("PUBLICATION RATE ANALYSIS (Publications per Year Post-Residency)\n")
        f.write("Controlling for Time Since Graduation\n")
        f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        # Overall statistics
        f.write("OVERALL STATISTICS\n")
        f.write("-" * 40 + "\n")
        f.write(f"Total residents: {len(df)}\n")
        f.write(f"Academic: {len(df[df['post_residency_career_type'] == 'Academic'])}\n")
        f.write(f"Private: {len(df[df['post_residency_career_type'] == 'Private'])}\n\n")
        
        # Separate by career type
        academic = df[df['post_residency_career_type'] == 'Academic']
        private = df[df['post_residency_career_type'] == 'Private']
        
        # Years post-graduation comparison
        f.write("\n" + "=" * 80 + "\n")
        f.write("TIME SINCE GRADUATION COMPARISON\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("Years Post-Graduation - Academic:\n")
        f.write(f"  Mean ± SD: {academic['years_post_graduation'].mean():.2f} ± {academic['years_post_graduation'].std():.2f}\n")
        f.write(f"  Median (IQR): {academic['years_post_graduation'].median():.1f} ({academic['years_post_graduation'].quantile(0.25):.1f} - {academic['years_post_graduation'].quantile(0.75):.1f})\n")
        f.write(f"  Range: {academic['years_post_graduation'].min()} - {academic['years_post_graduation'].max()}\n\n")
        
        f.write("Years Post-Graduation - Private:\n")
        f.write(f"  Mean ± SD: {private['years_post_graduation'].mean():.2f} ± {private['years_post_graduation'].std():.2f}\n")
        f.write(f"  Median (IQR): {private['years_post_graduation'].median():.1f} ({private['years_post_graduation'].quantile(0.25):.1f} - {private['years_post_graduation'].quantile(0.75):.1f})\n")
        f.write(f"  Range: {private['years_post_graduation'].min()} - {private['years_post_graduation'].max()}\n\n")
        
        # Test for difference in years post-graduation
        t_stat, p_val = stats.ttest_ind(academic['years_post_graduation'], private['years_post_graduation'])
        f.write(f"Independent t-test for years post-graduation:\n")
        f.write(f"  t = {t_stat:.3f}, p = {p_val:.4f}\n")
        if p_val < 0.05:
            f.write(f"  **SIGNIFICANT DIFFERENCE in years post-graduation between groups**\n")
            f.write(f"  This validates the need for rate-based analysis!\n\n")
        else:
            f.write(f"  No significant difference in years post-graduation\n\n")
        
        # RAW PUBLICATION COUNTS (for comparison)
        f.write("\n" + "=" * 80 + "\n")
        f.write("RAW PUBLICATION COUNTS (Not Controlled for Time)\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("Academic:\n")
        f.write(f"  Mean ± SD: {academic['total_publications'].mean():.1f} ± {academic['total_publications'].std():.1f}\n")
        f.write(f"  Median (IQR): {academic['total_publications'].median():.0f} ({academic['total_publications'].quantile(0.25):.0f} - {academic['total_publications'].quantile(0.75):.0f})\n")
        f.write(f"  Range: {academic['total_publications'].min()} - {academic['total_publications'].max()}\n")
        f.write(f"  % with >=1 publication: {(academic['total_publications'] > 0).mean() * 100:.1f}%\n\n")
        
        f.write("Private:\n")
        f.write(f"  Mean ± SD: {private['total_publications'].mean():.1f} ± {private['total_publications'].std():.1f}\n")
        f.write(f"  Median (IQR): {private['total_publications'].median():.0f} ({private['total_publications'].quantile(0.25):.0f} - {private['total_publications'].quantile(0.75):.0f})\n")
        f.write(f"  Range: {private['total_publications'].min()} - {private['total_publications'].max()}\n")
        f.write(f"  % with >=1 publication: {(private['total_publications'] > 0).mean() * 100:.1f}%\n\n")
        
        # PUBLICATION RATES (Controlled for time)
        f.write("\n" + "=" * 80 + "\n")
        f.write("PUBLICATION RATES (Publications per Year) - TIME CONTROLLED\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("Academic:\n")
        f.write(f"  Mean ± SD: {academic['publications_per_year'].mean():.3f} ± {academic['publications_per_year'].std():.3f} pubs/year\n")
        f.write(f"  Median (IQR): {academic['publications_per_year'].median():.3f} ({academic['publications_per_year'].quantile(0.25):.3f} - {academic['publications_per_year'].quantile(0.75):.3f})\n")
        f.write(f"  Range: {academic['publications_per_year'].min():.3f} - {academic['publications_per_year'].max():.3f}\n")
        f.write(f"  % with publication rate > 0: {(academic['publications_per_year'] > 0).mean() * 100:.1f}%\n\n")
        
        f.write("Private:\n")
        f.write(f"  Mean ± SD: {private['publications_per_year'].mean():.3f} ± {private['publications_per_year'].std():.3f} pubs/year\n")
        f.write(f"  Median (IQR): {private['publications_per_year'].median():.3f} ({private['publications_per_year'].quantile(0.25):.3f} - {private['publications_per_year'].quantile(0.75):.3f})\n")
        f.write(f"  Range: {private['publications_per_year'].min():.3f} - {private['publications_per_year'].max():.3f}\n")
        f.write(f"  % with publication rate > 0: {(private['publications_per_year'] > 0).mean() * 100:.1f}%\n\n")

        # Impact factor analysis (5-year IF merged from resident_avg_if.csv)
        if 'avg_if' in df.columns:
            f.write("\n" + "=" * 80 + "\n")
            f.write("IMPACT FACTOR (5-YEAR) BY CAREER TYPE\n")
            f.write("=" * 80 + "\n\n")

            valid_if = df[~df['avg_if'].isna()]
            f.write(f"Residents with IF data: {len(valid_if)} of {len(df)}\n")
            academic_if = valid_if[valid_if['post_residency_career_type'] == 'Academic']['avg_if']
            private_if = valid_if[valid_if['post_residency_career_type'] == 'Private']['avg_if']

            def write_if_stats(label, series):
                f.write(f"{label} (n={len(series)}):\n")
                if len(series) == 0:
                    f.write("  No data\n")
                    return
                f.write(f"  Mean ± SD: {series.mean():.2f} ± {series.std():.2f}\n")
                f.write(f"  Median (IQR): {series.median():.2f} ({series.quantile(0.25):.2f} - {series.quantile(0.75):.2f})\n")
                f.write(f"  Range: {series.min():.2f} - {series.max():.2f}\n\n")

            write_if_stats("Academic", academic_if)
            write_if_stats("Private", private_if)

            if len(academic_if) > 1 and len(private_if) > 1:
                # Welch's t-test
                t_if, p_if = stats.ttest_ind(academic_if, private_if, equal_var=False)
                f.write(f"Welch's t-test (IF): t = {t_if:.3f}, p = {p_if:.4f}\n")
                # Mann-Whitney
                u_if, p_if_mw = stats.mannwhitneyu(academic_if, private_if, alternative='two-sided')
                f.write(f"Mann-Whitney U (IF): U = {u_if:.1f}, p = {p_if_mw:.4f}\n")
                # Effect size
                mean_diff_if = academic_if.mean() - private_if.mean()
                pooled_if = np.sqrt((academic_if.std()**2 + private_if.std()**2) / 2)
                cohens_d_if = mean_diff_if / pooled_if if pooled_if > 0 else 0
                f.write(f"Effect Size (Cohen's d) IF: {cohens_d_if:.3f}\n\n")
            else:
                f.write("Not enough data for IF statistical comparison.\n\n")
        
        # Statistical tests on RATES
        f.write("\n" + "=" * 80 + "\n")
        f.write("STATISTICAL TESTS ON PUBLICATION RATES\n")
        f.write("=" * 80 + "\n\n")
        
        # T-test
        f.write("Welch's t-test (unequal variances):\n")
        t_stat, p_val = stats.ttest_ind(academic['publications_per_year'], 
                                        private['publications_per_year'], 
                                        equal_var=False)
        f.write(f"  t = {t_stat:.3f}, p = {p_val:.4f}\n")
        if p_val < 0.05:
            f.write(f"  **SIGNIFICANT DIFFERENCE in publication rates**\n\n")
        else:
            f.write(f"  No significant difference in publication rates\n\n")
        
        # Mann-Whitney U test (non-parametric)
        f.write("Mann-Whitney U test (non-parametric):\n")
        u_stat, p_val_mw = stats.mannwhitneyu(academic['publications_per_year'], 
                                              private['publications_per_year'], 
                                              alternative='two-sided')
        f.write(f"  U = {u_stat:.1f}, p = {p_val_mw:.4f}\n")
        if p_val_mw < 0.05:
            f.write(f"  **SIGNIFICANT DIFFERENCE in publication rates**\n\n")
        else:
            f.write(f"  No significant difference in publication rates\n\n")
        
        # Effect size (Cohen's d)
        mean_diff = academic['publications_per_year'].mean() - private['publications_per_year'].mean()
        pooled_std = np.sqrt((academic['publications_per_year'].std()**2 + private['publications_per_year'].std()**2) / 2)
        cohens_d = mean_diff / pooled_std
        f.write(f"Effect Size (Cohen's d): {cohens_d:.3f}\n")
        if abs(cohens_d) < 0.2:
            f.write("  (Small effect)\n\n")
        elif abs(cohens_d) < 0.5:
            f.write("  (Small to medium effect)\n\n")
        elif abs(cohens_d) < 0.8:
            f.write("  (Medium to large effect)\n\n")
        else:
            f.write("  (Large effect)\n\n")
        
        # ANCOVA-style analysis - comparing rates while controlling for years post-graduation
        f.write("\n" + "=" * 80 + "\n")
        f.write("LINEAR REGRESSION: Rate ~ Career Type + Years Post-Graduation\n")
        f.write("=" * 80 + "\n\n")
        
        df_reg = df.copy()
        df_reg['career_binary'] = (df_reg['post_residency_career_type'] == 'Academic').astype(int)
        
        X = df_reg[['career_binary', 'years_post_graduation']]
        X = sm.add_constant(X)
        y = df_reg['publications_per_year']
        
        model = sm.OLS(y, X).fit()
        f.write(str(model.summary()))
        f.write("\n\n")
        
        f.write("Interpretation:\n")
        f.write(f"  Controlling for years post-graduation, academics publish at a rate\n")
        f.write(f"  that is {model.params['career_binary']:.3f} publications/year {'higher' if model.params['career_binary'] > 0 else 'lower'}\n")
        f.write(f"  than private practitioners (p = {model.pvalues['career_binary']:.4f})\n\n")
        
        # Distribution by years post-graduation
        f.write("\n" + "=" * 80 + "\n")
        f.write("PUBLICATION RATES BY TIME COHORTS\n")
        f.write("=" * 80 + "\n\n")
        
        # Create cohorts
        df['cohort'] = pd.cut(df['years_post_graduation'], 
                              bins=[0, 3, 6, 10, 100],
                              labels=['1-3 years', '4-6 years', '7-10 years', '>10 years'])
        
        for cohort in ['1-3 years', '4-6 years', '7-10 years', '>10 years']:
            cohort_data = df[df['cohort'] == cohort]
            if len(cohort_data) == 0:
                continue
                
            f.write(f"\n{cohort} post-graduation (n={len(cohort_data)}):\n")
            f.write("-" * 40 + "\n")
            
            academic_cohort = cohort_data[cohort_data['post_residency_career_type'] == 'Academic']
            private_cohort = cohort_data[cohort_data['post_residency_career_type'] == 'Private']
            
            if len(academic_cohort) > 0:
                f.write(f"  Academic (n={len(academic_cohort)}):\n")
                f.write(f"    Mean rate: {academic_cohort['publications_per_year'].mean():.3f} pubs/year\n")
                f.write(f"    Median rate: {academic_cohort['publications_per_year'].median():.3f} pubs/year\n")
            
            if len(private_cohort) > 0:
                f.write(f"  Private (n={len(private_cohort)}):\n")
                f.write(f"    Mean rate: {private_cohort['publications_per_year'].mean():.3f} pubs/year\n")
                f.write(f"    Median rate: {private_cohort['publications_per_year'].median():.3f} pubs/year\n")
            
            if len(academic_cohort) > 1 and len(private_cohort) > 1:
                t_stat, p_val = stats.ttest_ind(academic_cohort['publications_per_year'],
                                                private_cohort['publications_per_year'],
                                                equal_var=False)
                f.write(f"  t-test: t={t_stat:.3f}, p={p_val:.4f}\n")
    
    print(f"\nAnalysis complete! Results saved to: {stats_file}")
    
    # Create visualizations
    create_rate_visualizations(df, output_dir)


def create_rate_visualizations(df, output_dir):
    """Create visualizations for publication rate analysis"""
    
    # Set style
    sns.set_style("whitegrid")
    
    # 1. Box plot of publication rates
    fig, ax = plt.subplots(figsize=(10, 6))
    academic = df[df['post_residency_career_type'] == 'Academic']['publications_per_year']
    private = df[df['post_residency_career_type'] == 'Private']['publications_per_year']
    
    bp = ax.boxplot([academic, private], labels=['Academic', 'Private'],
                     patch_artist=True, showmeans=True)
    bp['boxes'][0].set_facecolor('lightblue')
    bp['boxes'][1].set_facecolor('lightcoral')
    
    ax.set_ylabel('Publications per Year', fontsize=12)
    ax.set_title('Publication Rates Post-Residency by Career Type', fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'publication_rates_boxplot.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. Scatter plot: Rate vs Years Post-Graduation
    fig, ax = plt.subplots(figsize=(12, 7))
    
    academic_df = df[df['post_residency_career_type'] == 'Academic']
    private_df = df[df['post_residency_career_type'] == 'Private']
    
    ax.scatter(academic_df['years_post_graduation'], academic_df['publications_per_year'],
               alpha=0.6, s=60, c='blue', label='Academic', edgecolors='black', linewidth=0.5)
    ax.scatter(private_df['years_post_graduation'], private_df['publications_per_year'],
               alpha=0.6, s=60, c='red', label='Private', edgecolors='black', linewidth=0.5)
    
    # Add trend lines
    z_academic = np.polyfit(academic_df['years_post_graduation'], academic_df['publications_per_year'], 1)
    p_academic = np.poly1d(z_academic)
    z_private = np.polyfit(private_df['years_post_graduation'], private_df['publications_per_year'], 1)
    p_private = np.poly1d(z_private)
    
    x_line = np.linspace(df['years_post_graduation'].min(), df['years_post_graduation'].max(), 100)
    ax.plot(x_line, p_academic(x_line), "b--", linewidth=2, label='Academic trend')
    ax.plot(x_line, p_private(x_line), "r--", linewidth=2, label='Private trend')
    
    ax.set_xlabel('Years Post-Graduation', fontsize=12)
    ax.set_ylabel('Publications per Year', fontsize=12)
    ax.set_title('Publication Rate vs Time Since Graduation', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'rate_vs_years_scatter.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    # 3. Histogram of publication rates
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    ax1.hist(academic, bins=30, alpha=0.7, color='blue', edgecolor='black')
    ax1.axvline(academic.mean(), color='darkblue', linestyle='--', linewidth=2, label=f'Mean: {academic.mean():.3f}')
    ax1.axvline(academic.median(), color='cyan', linestyle='--', linewidth=2, label=f'Median: {academic.median():.3f}')
    ax1.set_xlabel('Publications per Year', fontsize=11)
    ax1.set_ylabel('Frequency', fontsize=11)
    ax1.set_title('Academic - Publication Rate Distribution', fontsize=12, fontweight='bold')
    ax1.legend()
    ax1.grid(alpha=0.3)
    
    ax2.hist(private, bins=30, alpha=0.7, color='red', edgecolor='black')
    ax2.axvline(private.mean(), color='darkred', linestyle='--', linewidth=2, label=f'Mean: {private.mean():.3f}')
    ax2.axvline(private.median(), color='orange', linestyle='--', linewidth=2, label=f'Median: {private.median():.3f}')
    ax2.set_xlabel('Publications per Year', fontsize=11)
    ax2.set_ylabel('Frequency', fontsize=11)
    ax2.set_title('Private - Publication Rate Distribution', fontsize=12, fontweight='bold')
    ax2.legend()
    ax2.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'rate_distributions.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Visualizations saved to: {output_dir}")


if __name__ == "__main__":
    # Update these paths as needed
    csv_file = "new_post_residency_with_if.csv"  # Joined with resident_avg_if.csv
    output_dir = "analysis"
    
    analyze_publication_rates(csv_file, output_dir)
