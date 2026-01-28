
import os
from datetime import datetime

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
from matplotlib.backends.backend_pdf import PdfPages
from sklearn.metrics import roc_auc_score, roc_curve
from util.effect_size import print_cohens_d
from util.mannwhitney import print_mannwhitney
from util.odds_ratio import print_odds_ratio
from util.pearson_corr import print_pearson_correlation
from util.robust_stats import print_median_iqr, print_prop_above_threshold
from util.ttest import print_ttest_summary, print_welchs_ttest
from util.zero_inflated import fit_zero_inflated_poisson, print_zip_summary

matplotlib.use('Agg')

def analyze_data(df, period, output_dir):

    """Perform analysis on either during or post residency data"""
    # Create output files
    stats_file = os.path.join(output_dir, f'analysis_stats_{period}.txt')
    pdf_file = os.path.join(output_dir, f'analysis_plots_{period}.pdf')
    
    # Calculate publication rates for post-residency data (if years_post_graduation is present)
    if 'years_post_graduation' in df.columns and period == 'post_residency':
        # Calculate publications per year
        df['publications_per_year'] = df.apply(
            lambda row: row['total_publications'] / row['years_post_graduation'] 
            if row['years_post_graduation'] > 0 else 0, axis=1
        )
    
    # Convert career type to binary
    df['career_binary'] = (df['post_residency_career_type'] == 'Academic').astype(int)
    X = df[['total_publications']]
    X = sm.add_constant(X)
    y = df['career_binary']
    
    # Fit logistic regression model
    model = sm.Logit(y, X).fit()
    
    # Get predictions
    df['predicted_prob'] = model.predict(X)
    
    # Separate data by career type
    academic_pubs = df[df['post_residency_career_type'] == 'Academic']['total_publications']
    private_pubs = df[df['post_residency_career_type'] == 'Private']['total_publications']
    
        # Output predicted probability of academic career for publication bins
    bins = [(0, 0), (1, 4), (5, 9), (10, 14), (15, 30)]
    bin_labels = ["0", "1–4", "5–9", "10–14", "15+"]
    coef = model.params['total_publications']
    intercept = model.params['const']

        


    # Only save plots for during_residency period
    save_plots = (period == 'during_residency')
    # Open files and perform analysis
    with PdfPages(pdf_file) as pdf, open(stats_file, 'w') as f:
        # Write basic info
        f.write(f"Analysis Report for {period.replace('_', ' ').title()} Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Shape of data: {df.shape}\n\n")

        f.write("\nPredicted Probability of Academic Career by Publication Count Bin:\n")
        for (low, high), label in zip(bins, bin_labels):
            if low == high:
                x = low
                prob = 1/(1 + np.exp(-(intercept + coef * x)))
                f.write(f"{label} publications: {prob:.2f}\n")
            else:
                x_mid = (low + high) / 2
                prob_low = 1/(1 + np.exp(-(intercept + coef * low)))
                prob_high = 1/(1 + np.exp(-(intercept + coef * high)))
                prob_mid = 1/(1 + np.exp(-(intercept + coef * x_mid)))
                f.write(f"{label} publications: {prob_low:.2f}–{prob_high:.2f} (midpoint: {prob_mid:.2f})\n")

        # Model Summary
        f.write("Logistic Regression Model Summary:\n")
        f.write(str(model.summary()))
        f.write("\n\n")

        # Publication Statistics
        f.write("Publication Statistics by Career Type:\n")
        summary_stats = df.groupby('post_residency_career_type')['total_publications'].agg([
            'count', 'mean', 'std', 'min', 'median', 'max'
        ])
        if not summary_stats.empty:
            f.write(summary_stats.to_string())
        else:
            f.write("No data available for summary statistics.\n")
        f.write("\n\n")

    # For post-residency data, add time-controlled analysis
        if 'years_post_graduation' in df.columns and period == 'post_residency':
            f.write("="*80 + "\n")
            f.write("TIME SINCE GRADUATION ANALYSIS\n")
            f.write("="*80 + "\n\n")

            academic_years = df[df['post_residency_career_type'] == 'Academic']['years_post_graduation']
            private_years = df[df['post_residency_career_type'] == 'Private']['years_post_graduation']

            f.write("Years Post-Graduation - Academic:\n")
            f.write(f"  Mean ± SD: {academic_years.mean():.2f} ± {academic_years.std():.2f}\n")
            f.write(f"  Median (IQR): {academic_years.median():.1f} ({academic_years.quantile(0.25):.1f} - {academic_years.quantile(0.75):.1f})\n")
            f.write(f"  Range: {academic_years.min()} - {academic_years.max()}\n\n")

            f.write("Years Post-Graduation - Private:\n")
            f.write(f"  Mean ± SD: {private_years.mean():.2f} ± {private_years.std():.2f}\n")
            f.write(f"  Median (IQR): {private_years.median():.1f} ({private_years.quantile(0.25):.1f} - {private_years.quantile(0.75):.1f})\n")
            f.write(f"  Range: {private_years.min()} - {private_years.max()}\n\n")

            # Test for difference in years post-graduation
            from scipy import stats as scipy_stats
            t_stat_years, p_val_years = scipy_stats.ttest_ind(academic_years, private_years, equal_var=False)
            f.write(f"Welch's t-test for years post-graduation:\n")
            f.write(f"  t = {t_stat_years:.3f}, p = {p_val_years:.4f}\n")
            if p_val_years < 0.05:
                f.write(f"  **SIGNIFICANT DIFFERENCE in time since graduation between groups**\n")
                f.write(f"  This validates the need for rate-based analysis!\n\n")
            else:
                f.write(f"  No significant difference in time since graduation\n\n")

            f.write("="*80 + "\n")
            f.write("PUBLICATION RATE ANALYSIS (Publications per Year)\n")
            f.write("="*80 + "\n\n")

            academic_rate = df[df['post_residency_career_type'] == 'Academic']['publications_per_year']
            private_rate = df[df['post_residency_career_type'] == 'Private']['publications_per_year']

            f.write("Academic - Publication Rate:\n")
            f.write(f"  Mean ± SD: {academic_rate.mean():.3f} ± {academic_rate.std():.3f} pubs/year\n")
            f.write(f"  Median (IQR): {academic_rate.median():.3f} ({academic_rate.quantile(0.25):.3f} - {academic_rate.quantile(0.75):.3f})\n")
            f.write(f"  Range: {academic_rate.min():.3f} - {academic_rate.max():.3f}\n")
            f.write(f"  % with rate > 0: {(academic_rate > 0).mean() * 100:.1f}%\n\n")

            f.write("Private - Publication Rate:\n")
            f.write(f"  Mean ± SD: {private_rate.mean():.3f} ± {private_rate.std():.3f} pubs/year\n")
            f.write(f"  Median (IQR): {private_rate.median():.3f} ({private_rate.quantile(0.25):.3f} - {private_rate.quantile(0.75):.3f})\n")
            f.write(f"  Range: {private_rate.min():.3f} - {private_rate.max():.3f}\n")
            f.write(f"  % with rate > 0: {(private_rate > 0).mean() * 100:.1f}%\n\n")

            # Statistical tests on rates
            f.write("Statistical Tests on Publication Rates:\n")
            f.write("-" * 40 + "\n")

            t_stat_rate, p_val_rate = scipy_stats.ttest_ind(academic_rate, private_rate, equal_var=False)
            f.write(f"Welch's t-test on rates: t = {t_stat_rate:.3f}, p = {p_val_rate:.4f}\n")

            u_stat_rate, p_val_mw_rate = scipy_stats.mannwhitneyu(academic_rate, private_rate, alternative='two-sided')
            f.write(f"Mann-Whitney U test on rates: U = {u_stat_rate:.1f}, p = {p_val_mw_rate:.4f}\n")

            # Effect size for rates
            mean_diff_rate = academic_rate.mean() - private_rate.mean()
            pooled_std_rate = np.sqrt((academic_rate.std()**2 + private_rate.std()**2) / 2)
            cohens_d_rate = mean_diff_rate / pooled_std_rate if pooled_std_rate > 0 else 0
            f.write(f"Cohen's d (effect size) for rates: {cohens_d_rate:.3f}\n")
            if abs(cohens_d_rate) < 0.2:
                f.write("  (Small effect)\n")
            elif abs(cohens_d_rate) < 0.5:
                f.write("  (Small to medium effect)\n")
            elif abs(cohens_d_rate) < 0.8:
                f.write("  (Medium to large effect)\n")
            else:
                f.write("  (Large effect)\n")
            f.write("\n")

            # Linear regression: Rate ~ Career Type + Years Post-Graduation
            f.write("="*80 + "\n")
            f.write("LINEAR REGRESSION: Rate ~ Career Type + Years Post-Graduation\n")
            f.write("="*80 + "\n\n")

            X_rate = df[['career_binary', 'years_post_graduation']]
            X_rate = sm.add_constant(X_rate)
            y_rate = df['publications_per_year']

            model_rate = sm.OLS(y_rate, X_rate).fit()
            f.write(str(model_rate.summary()))
            f.write("\n\n")

            f.write("INTERPRETATION:\n")
            f.write(f"Controlling for years post-graduation, academics publish at a rate\n")
            f.write(f"that is {model_rate.params['career_binary']:.4f} publications/year ")
            f.write(f"{'higher' if model_rate.params['career_binary'] > 0 else 'lower'} than private practitioners\n")
            f.write(f"(p = {model_rate.pvalues['career_binary']:.4f})\n\n")

            f.write("="*80 + "\n\n")

        # T-test for difference in means between Academic and Private
        if len(academic_pubs) > 1 and len(private_pubs) > 1:
            f.write(print_ttest_summary(academic_pubs, private_pubs, label1='Academic', label2='Private') + "\n")
        else:
            f.write("Not enough data for t-test between Academic and Private groups.\n\n")

        # Mann-Whitney U test
        f.write(print_mannwhitney(academic_pubs, private_pubs, label1='Academic', label2='Private') + "\n")

        # Welch's t-test
        f.write(print_welchs_ttest(academic_pubs, private_pubs, label1='Academic', label2='Private') + "\n")

        # Effect Size
        f.write(print_cohens_d(academic_pubs, private_pubs, label1='Academic', label2='Private') + "\n")

        # Odds Ratio Analysis
        f.write(print_odds_ratio(model, param_name='total_publications') + "\n")

        # ROC Analysis
        fpr, tpr, _ = roc_curve(y, df['predicted_prob'])
        roc_auc = roc_auc_score(y, df['predicted_prob'])
        f.write(f"ROC AUC Score: {roc_auc:.3f}\n\n")

        # Pearson correlation between during- and post-residency publications (if both columns exist)
        if 'post_residency_publications' in df.columns:
            pearson_text = print_pearson_correlation(df['total_publications'], df['post_residency_publications'], labelx='During Residency', labely='Post Residency')
            f.write(pearson_text + "\n")

        # Median and IQR for each group
        f.write("Median and IQR by Career Type:\n")
        f.write(print_median_iqr(academic_pubs, label='Academic'))
        f.write(print_median_iqr(private_pubs, label='Private'))
        f.write("\n")

        # Proportion with >=1 publication
        f.write("Proportion with >=1 publication by Career Type:\n")
        f.write(print_prop_above_threshold(academic_pubs, label='Academic', threshold=1))
        f.write(print_prop_above_threshold(private_pubs, label='Private', threshold=1))
        f.write("\n")
        # Zero-inflated Poisson regression (if both groups have zeros)
        if (academic_pubs == 0).any() or (private_pubs == 0).any():
            try:
                y = df['total_publications']
                X = sm.add_constant(df['career_binary'])
                zip_result = fit_zero_inflated_poisson(y, X)
                f.write("Zero-Inflated Poisson Regression Summary:\n")
                f.write(print_zip_summary(zip_result) + "\n")
            except Exception as e:
                f.write(f"Zero-Inflated Poisson model failed: {e}\n\n")

        # Compare research output between women and men
        if 'sex' in df.columns:
            female_pubs = df[df['sex'].str.lower().isin(['female', 'f'])]['total_publications']
            male_pubs = df[df['sex'].str.lower().isin(['male', 'm'])]['total_publications']
            f.write("\n--- Sex Comparison: Research Output (All Career Types) ---\n")
            f.write(f"N Female: {len(female_pubs)}, N Male: {len(male_pubs)}\n")
            f.write(f"Female Mean (SD): {female_pubs.mean():.2f} ({female_pubs.std():.2f}), Median (IQR): {female_pubs.median():.2f} ({female_pubs.quantile(0.75)-female_pubs.quantile(0.25):.2f})\n")
            f.write(f"Male Mean (SD): {male_pubs.mean():.2f} ({male_pubs.std():.2f}), Median (IQR): {male_pubs.median():.2f} ({male_pubs.quantile(0.75)-male_pubs.quantile(0.25):.2f})\n")
            if len(female_pubs) > 1 and len(male_pubs) > 1:
                f.write(print_ttest_summary(female_pubs, male_pubs, label1='Female', label2='Male') + "\n")
                f.write(print_mannwhitney(female_pubs, male_pubs, label1='Female', label2='Male') + "\n")
                f.write(print_welchs_ttest(female_pubs, male_pubs, label1='Female', label2='Male') + "\n")
                f.write(print_cohens_d(female_pubs, male_pubs, label1='Female', label2='Male') + "\n")
            else:
                f.write("Not enough data for statistical comparison between women and men.\n\n")

        # Subgroup analysis: Sex and Fellowship (removed institution-level stats per request)
        subgroup_vars = [('sex', 'Sex'), ('fellowship', 'Fellowship')]
        for col, label in subgroup_vars:
            if col in df.columns:
                f.write(f"\n--- Subgroup Analysis: {label} ---\n")
                for subgroup, subdf in df.groupby(col):
                    f.write(f"\n{label}: {subgroup}\n")
                    # Publication stats
                    stats = subdf.groupby('post_residency_career_type')['total_publications'].agg([
                        'count', 'mean', 'std', 'min', 'median', 'max'
                    ])
                    f.write("Publication Statistics by Career Type:\n")
                    if not stats.empty:
                        f.write(stats.to_string())
                    else:
                        f.write("No data available for summary statistics.\n")
                    f.write("\n")
                    # Academic placement rate
                    placement = subdf['post_residency_career_type'].value_counts(normalize=True)
                    for career, pct in placement.items():
                        f.write(f"{career} placement: {pct*100:.1f}%\n")
                    f.write("\n")
                    # If enough data, t-test and effect size
                    ac = subdf[subdf['post_residency_career_type']=='Academic']['total_publications']
                    pr = subdf[subdf['post_residency_career_type']=='Private']['total_publications']
                    if len(ac) > 1 and len(pr) > 1:
                        f.write(print_ttest_summary(ac, pr, label1='Academic', label2='Private') + "\n")
                        f.write(print_mannwhitney(ac, pr, label1='Academic', label2='Private') + "\n")
                        f.write(print_welchs_ttest(ac, pr, label1='Academic', label2='Private') + "\n")
                        f.write(print_cohens_d(ac, pr, label1='Academic', label2='Private') + "\n")
                    else:
                        f.write("Not enough data for t-test between Academic and Private groups.\n\n")

        if save_plots:
            # Combined Figure: 1A = boxplot (display-only remove extreme outlier), 1B = probability scatter (display-only remove points >65)
            fig, axes = plt.subplots(1, 2, figsize=(14, 6))

            # Boxplot (1A) - for display, hide extreme outliers above a visualization threshold (e.g., 65)
            # Create a copy for plotting so we don't alter df
            plot_df = df.copy()
            # Mark values above threshold as NaN for the boxplot visualization only
            plot_df['total_publications_plot'] = plot_df['total_publications'].where(plot_df['total_publications'] <= 95, np.nan)
            sns.boxplot(x='post_residency_career_type', y='total_publications_plot', data=plot_df, palette={'Academic': "#2d4b8f", 'Private': '#c43a39'}, ax=axes[0])
            # Overlay the full-data small markers for the inliers (so outlier isn't shown)
            # sns.stripplot(x='post_residency_career_type', y='total_publications', data=plot_df[plot_df['total_publications'] <= 125], color='black', alpha=0.4, jitter=True, ax=axes[0])
            axes[0].set_xlabel('Career Type')
            axes[0].set_ylabel('Publication Count')
            axes[0].set_title('Publication Distribution (During Residency)')
            # Add Mann-Whitney U test p-value annotation
            from scipy.stats import mannwhitneyu
            acad = df[df['post_residency_career_type'] == 'Academic']['total_publications']
            priv = df[df['post_residency_career_type'] == 'Private']['total_publications']
            if len(acad) > 1 and len(priv) > 1:
                stat, p_val = mannwhitneyu(acad, priv, alternative='greater')
                axes[0].text(0.5, 0.92, f"p = {p_val:.4f}", transform=axes[0].transAxes, ha='center', va='top', fontsize=10, color='black')
            else:
                axes[0].text(0.5, 0.92, "Mann-Whitney U: N/A", transform=axes[0].transAxes, ha='center', va='top', fontsize=10, color='black')
            max_actual = df['total_publications'].max()
            
            # Probability plot (1B) - remove plotted points with publications > viz_threshold
            prob_df = df[df['total_publications'] <= 65]
            axes[1].scatter(prob_df['total_publications'], prob_df['predicted_prob'], alpha=0.5)
            axes[1].set_xlabel('Publication Count')
            axes[1].set_ylabel('Predicted Probability')
            axes[1].set_title('Probability of Pursuing an Academic Career Based on Research Productivity')
            # axes[1].set_ylim(-0.02, 1.02)

            plt.tight_layout()
            # Save combined figure both as PNG and into the PDF
            combined_png = os.path.join(output_dir, 'figure1_combined_box_prob.png')
            fig.savefig(combined_png, dpi=150)
            pdf.savefig(fig)
            plt.close(fig)

            # Plot 2: ROC Curve
            plt.figure(figsize=(8, 6))
            plt.plot(fpr, tpr, color='darkorange', lw=2, 
                    label=f'ROC curve (AUC = {roc_auc:.2f})')
            plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
            plt.xlim([0.0, 1.0])
            plt.ylim([0.0, 1.05])
            plt.xlabel('False Positive Rate', fontsize=12)
            plt.ylabel('True Positive Rate', fontsize=12)
            plt.title('ROC Curve for Publication Count\nvs Academic Career', fontsize=14)
            plt.legend(loc="lower right")

        # Add publication rate plots for post-residency data
        if 'publications_per_year' in df.columns and period == 'post_residency':
            # Boxplot of publication rates
            plt.figure(figsize=(8, 6))
            sns.boxplot(x='post_residency_career_type', y='publications_per_year', 
                       data=df, palette={'Academic': "#2d4b8f", 'Private': '#c43a39'})
            plt.xlabel('Career Type', fontsize=12)
            plt.ylabel('Publications per Year', fontsize=12)
            plt.title('Publication Rate (Pubs/Year) by Career Type\nTime-Controlled Analysis', fontsize=14)
            plt.tight_layout()
            rate_boxplot_png = os.path.join(output_dir, 'figure4_publication_rates_boxplot.png')
            plt.savefig(rate_boxplot_png, dpi=150)
            pdf.savefig()
            plt.close()

            # Scatter plot: Publication rate vs years post-graduation
            fig, ax = plt.subplots(figsize=(10, 6))
            academic_df = df[df['post_residency_career_type'] == 'Academic']
            private_df = df[df['post_residency_career_type'] == 'Private']
            ax.scatter(academic_df['years_post_graduation'], academic_df['publications_per_year'],
                      alpha=0.6, s=60, c='#2d4b8f', label='Academic', edgecolors='black', linewidth=0.5)
            ax.scatter(private_df['years_post_graduation'], private_df['publications_per_year'],
                      alpha=0.6, s=60, c='#c43a39', label='Private', edgecolors='black', linewidth=0.5)
            # Add trend lines
            if len(academic_df) > 1:
                z_academic = np.polyfit(academic_df['years_post_graduation'], academic_df['publications_per_year'], 1)
                p_academic = np.poly1d(z_academic)
                x_line = np.linspace(df['years_post_graduation'].min(), df['years_post_graduation'].max(), 100)
                ax.plot(x_line, p_academic(x_line), "#2d4b8f", linestyle='--', linewidth=2, label='Academic trend')
            if len(private_df) > 1:
                z_private = np.polyfit(private_df['years_post_graduation'], private_df['publications_per_year'], 1)
                p_private = np.poly1d(z_private)
                x_line = np.linspace(df['years_post_graduation'].min(), df['years_post_graduation'].max(), 100)
                ax.plot(x_line, p_private(x_line), "#c43a39", linestyle='--', linewidth=2, label='Private trend')
            ax.set_xlabel('Years Post-Graduation', fontsize=12)
            ax.set_ylabel('Publications per Year', fontsize=12)
            ax.set_title('Publication Rate vs Time Since Graduation', fontsize=14)
            ax.legend()
            ax.grid(alpha=0.3)
            plt.tight_layout()
            rate_scatter_png = os.path.join(output_dir, 'publication_rate_vs_years.png')
            plt.savefig(rate_scatter_png, dpi=150)
            pdf.savefig()
            plt.close()

            # Publication distribution (post-residency) by career type
            try:
                plt.figure(figsize=(8, 6))
                # Hide boxplot fliers (light gray dots) and overlay hollow circle markers
                sns.boxplot(x='post_residency_career_type', y='total_publications', data=df,
                            palette={'Academic': "#2d4b8f", 'Private': '#c43a39'}, showfliers=False)
                # Compute outliers (1.5 * IQR rule) per group and plot ONLY those as hollow circles
                groups = list(df['post_residency_career_type'].unique())
                for i, grp in enumerate(groups):
                    grp_values = df.loc[df['post_residency_career_type'] == grp, 'total_publications']
                    if grp_values.empty:
                        continue
                    q1 = grp_values.quantile(0.25)
                    q3 = grp_values.quantile(0.75)
                    iqr = q3 - q1
                    lower = q1 - 1.5 * iqr
                    upper = q3 + 1.5 * iqr
                    outliers = grp_values[(grp_values < lower) | (grp_values > upper)]
                    if not outliers.empty:
                        x = np.full(len(outliers), i)
                        plt.scatter(x, outliers.values, facecolors='none', edgecolors='black', s=36, linewidths=0.8, zorder=3)
                plt.xlabel('Career Type', fontsize=12)
                plt.ylabel('Publication Count', fontsize=12)
                plt.title('Publication Distribution \n Post Residency', fontsize=14)
                plt.tight_layout()
                # save standalone PNG for Figure 3 and add to PDF
                fig3_png = os.path.join(output_dir, 'figure3_post_residency_boxplot.png')
                # Save high-quality PNG for publication
                plt.savefig(fig3_png, dpi=300, bbox_inches='tight')
                pdf.savefig()
                plt.close()
            except Exception:
                # If plotting fails, continue without stopping analysis
                pass

            # Additional Plots: Boxplots by Sex and Fellowship (institution-level plots removed)
            if 'sex' in df.columns:
                plt.figure(figsize=(8, 6))
                sns.boxplot(x='sex', y='total_publications', hue='post_residency_career_type',
                            data=df, palette={'Academic': "#2d4b8f", 'Private': '#c43a39'})
                plt.xlabel('Sex', fontsize=12)
                plt.ylabel('Publication Count', fontsize=12)
                plt.title(f'Publication Count by Sex and Career Type\n{period.replace("_", " ").title()}', fontsize=14)
                plt.legend(title='Career Type')
                plt.tight_layout()
                pdf.savefig()
                plt.close()

            if 'fellowship' in df.columns:
                plt.figure(figsize=(8, 6))
                sns.boxplot(x='fellowship', y='total_publications', hue='post_residency_career_type',
                            data=df, palette={'Academic': "#2d4b8f", 'Private': '#c43a39'})
                plt.xlabel('Fellowship', fontsize=12)
                plt.ylabel('Publication Count', fontsize=12)
                plt.title(f'Publication Count by Fellowship and Career Type\n{period.replace("_", " ").title()}', fontsize=14)
                plt.legend(title='Career Type')
                plt.tight_layout()
                pdf.savefig()
                plt.close()

            # Export violin plot: During-residency publication counts by career path
            plt.figure(figsize=(8, 6))
            sns.violinplot(x='post_residency_career_type', y='total_publications', data=df, palette={'Academic': "#2d4b8f", 'Private': '#c43a39'}, inner='box')
            plt.xlabel('Career Path', fontsize=12)
            plt.ylabel('During-Residency Publication Count', fontsize=12)
            plt.title('During-Residency Publication Counts by Career Path', fontsize=14)
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'violinplot_during_publications.png'))
            plt.close()

            plt.tight_layout()
            pdf.savefig()
            plt.close()
        
    return stats_file, pdf_file

def main():
    REMOVE_OUTLIERS = False  # Toggle this to True to remove outliers based on IQR, False to keep them
    REMOVE_ZEROS = False  # Toggle this to True to remove rows with zero publications, False to keep them

    # Get the current script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Input files are now in the main Data Analysis folder
    post_csv_path = os.path.join(script_dir, 'new_post_residency.csv')
    during_csv_path = os.path.join(script_dir, 'new_during_residency.csv')

    # All output/results go into the analysis/ folder
    output_dir = os.path.join(script_dir, 'analysis')
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Read data
        df_during = pd.read_csv(during_csv_path)
        df_post = pd.read_csv(post_csv_path)

        # Clean data
        for df in [df_during, df_post]:
            df.replace([np.inf, -np.inf], np.nan, inplace=True)
            df.dropna(subset=['total_publications'], inplace=True)
            # Ensure correct dtypes for new columns
            if 'fellowship' in df.columns:
                df['fellowship'] = df['fellowship'].astype(str)
            if REMOVE_ZEROS:
                df.drop(df[df['total_publications'] == 0].index, inplace=True)
            if REMOVE_OUTLIERS:
                q1 = df['total_publications'].quantile(0.25)
                q3 = df['total_publications'].quantile(0.75)
                iqr = q3 - q1
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                df.drop(df[(df['total_publications'] < lower_bound) | (df['total_publications'] > upper_bound)].index, inplace=True)

        # Export Table 1: Combined summary table (Academic vs Private)
        # Use during-residency data for publication stats, add post-residency if available
        summary_rows = []
        for group, group_df in df_during.groupby('post_residency_career_type'):
            row = {'Career Path': group}
            row['N'] = len(group_df)
            # Demographics
            if 'sex' in group_df.columns:
                for sex_val, sex_count in group_df['sex'].value_counts().items():
                    row[f'Sex: {sex_val} (n,%)'] = f"{sex_count} ({sex_count/len(group_df)*100:.1f}%)"
            if 'fellowship' in group_df.columns:
                for fval, fcount in group_df['fellowship'].value_counts().items():
                    row[f'Fellowship: {fval} (n,%)'] = f"{fcount} ({fcount/len(group_df)*100:.1f}%)"
            if 'institution' in group_df.columns:
                for ival, icount in group_df['institution'].value_counts().items():
                    row[f'Institution: {ival} (n,%)'] = f"{icount} ({icount/len(group_df)*100:.1f}%)"
            # During-residency publication stats
            pubs = group_df['total_publications']
            row['During Mean'] = pubs.mean()
            row['During Median'] = pubs.median()
            row['During SD'] = pubs.std()
            row['During IQR'] = pubs.quantile(0.75) - pubs.quantile(0.25)
            row['During Min'] = pubs.min()
            row['During Max'] = pubs.max()
            # Post-residency publication stats (if available)
            if 'resident_id' in group_df.columns and 'resident_id' in df_post.columns:
                merged = pd.merge(group_df[['resident_id']], df_post[['resident_id','total_publications']], on='resident_id', how='left')
                post_pubs = merged['total_publications'].dropna()
                if not post_pubs.empty:
                    row['Post Mean'] = post_pubs.mean()
                    row['Post Median'] = post_pubs.median()
                    row['Post SD'] = post_pubs.std()
                    row['Post IQR'] = post_pubs.quantile(0.75) - post_pubs.quantile(0.25)
                    row['Post Min'] = post_pubs.min()
                    row['Post Max'] = post_pubs.max()
            summary_rows.append(row)
        summary_df = pd.DataFrame(summary_rows)
        summary_df.to_csv(os.path.join(output_dir, 'table1_summary.csv'), index=False)

        plt.figure(figsize=(8, 6))
        sns.boxplot(x='post_residency_career_type', y='total_publications', data=df_during, palette={'Academic': "#2d4b8f", 'Private': '#c43a39'})
        sns.stripplot(x='post_residency_career_type', y='total_publications', data=df_during, color='black', alpha=0.4, jitter=True)
        plt.xlabel('Career Path', fontsize=12)
        plt.ylabel('During-Residency Publication Count', fontsize=12)
        plt.title('During-Residency Publication Counts by Career Path', fontsize=14)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'boxplot_during_publications.png'))
        plt.close()

        during_stats, during_plots = analyze_data(df_during, 'during_residency', output_dir)
        post_stats, post_plots = analyze_data(df_post, 'post_residency', output_dir)

        if 'resident_id' in df_during.columns and 'resident_id' in df_post.columns:
            merged = pd.merge(df_during[['resident_id', 'total_publications']],
                             df_post[['resident_id', 'total_publications']],
                             on='resident_id',
                             suffixes=('_during', '_post'))
            pearson_text = print_pearson_correlation(
                merged['total_publications_during'],
                merged['total_publications_post'],
                labelx='During Residency',
                labely='Post Residency')
            print(pearson_text)

            with open(os.path.join(output_dir, 'pearson_correlation.txt'), 'w') as pf:
                pf.write(pearson_text)

        print("\nAnalysis complete! Results have been saved to:")
        print("\nDuring Residency Analysis:")
        print(f"Statistics: {during_stats}")
        print(f"Plots: {during_plots}")
        print("\nPost Residency Analysis:")
        print(f"Statistics: {post_stats}")
        print(f"Plots: {post_plots}")
        # Write figure captions mapping file
        captions_path = os.path.join(output_dir, 'figure_captions.md')
        try:
            with open(captions_path, 'w') as cf:
                cf.write("# Figure captions and filenames\n\n")
                cf.write("Figure 1 (A,B): figure1_combined_box_prob.png - (A) Boxplot showing the distribution of publication counts during residency by career path; (B) Scatter plot of total publication counts during residency versus predicted probability of pursuing an academic career.\n\n")
                cf.write("Figure 2: violinplot_during_publications.png - Violin plot illustrating the distribution and density of publication counts during residency for academic and private career paths.\n\n")
                cf.write("Figure 3: figure3_post_residency_boxplot.png - Boxplot showing the distribution of publication counts after residency by career path (academic versus private).\n\n")
                cf.write("Figure 4: figure4_publication_rates_boxplot.png - Publication rate (publications per year) by career type (time-controlled).\n")
            print(f"Figure captions saved to: {captions_path}")
        except Exception:
            pass
        
    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Working directory: {os.getcwd()}")
        print(f"Looking for files at: {post_csv_path} and {during_csv_path}")

if __name__ == "__main__":
    main()
    main()
