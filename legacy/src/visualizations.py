"""
Visualization Generation for iMessage Wrapped
Creates beautiful, shareable charts and images
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import pandas as pd
from typing import Dict, List, Tuple
from .utils import format_number, format_duration, anonymize_contact


# iMessage color scheme
IMESSAGE_BLUE = '#007AFF'
IMESSAGE_GREEN = '#34C759'
IMESSAGE_GRAY = '#E5E5EA'
BACKGROUND_COLOR = '#000000'
TEXT_COLOR = '#FFFFFF'
ACCENT_COLOR = '#5856D6'


class VisualizationGenerator:
    """Generates shareable visualizations"""

    def __init__(self, output_dir: str = "output"):
        """
        Initialize visualization generator

        Args:
            output_dir: Directory to save images
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Set style
        sns.set_style("dark")
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']

    def create_summary_card(self, stats: Dict, period: str, filename: str = "summary.png"):
        """
        Create summary statistics card

        Args:
            stats: Dictionary with summary statistics
            period: "Past Year" or "All Time"
            filename: Output filename
        """
        fig = plt.figure(figsize=(10, 12), facecolor=BACKGROUND_COLOR)

        # Create gradient background
        ax = fig.add_subplot(111)
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 12)
        ax.axis('off')

        # Title
        ax.text(5, 11, 'iMessage Wrapped', ha='center', va='top',
                fontsize=48, fontweight='bold', color=TEXT_COLOR)

        ax.text(5, 10.2, period, ha='center', va='top',
                fontsize=24, color=IMESSAGE_BLUE)

        # Main stats
        y_pos = 8.5
        stats_to_show = [
            (format_number(stats['total_messages']), 'Total Messages', IMESSAGE_BLUE),
            (format_number(stats['messages_sent']), 'Messages Sent', IMESSAGE_GREEN),
            (format_number(stats['messages_received']), 'Messages Received', ACCENT_COLOR),
            (str(stats['contacts']), 'Contacts', TEXT_COLOR),
        ]

        for value, label, color in stats_to_show:
            ax.text(5, y_pos, value, ha='center', va='center',
                    fontsize=56, fontweight='bold', color=color)
            ax.text(5, y_pos - 0.6, label, ha='center', va='center',
                    fontsize=20, color=TEXT_COLOR, alpha=0.7)
            y_pos -= 2

        # Footer
        ax.text(5, 0.5, 'Your year in texts', ha='center', va='center',
                fontsize=18, color=TEXT_COLOR, alpha=0.5)

        plt.tight_layout()
        plt.savefig(self.output_dir / filename, dpi=300, facecolor=BACKGROUND_COLOR,
                    bbox_inches='tight', pad_inches=0.3)
        plt.close()

    def create_top_contacts_chart(self, contacts_df: pd.DataFrame,
                                   anonymize: bool = False,
                                   filename: str = "top_contacts.png"):
        """
        Create top contacts horizontal bar chart

        Args:
            contacts_df: DataFrame from get_top_contacts()
            anonymize: Whether to anonymize contact names
            filename: Output filename
        """
        if len(contacts_df) == 0:
            return

        fig, ax = plt.subplots(figsize=(12, 8), facecolor=BACKGROUND_COLOR)

        # Prepare data
        df = contacts_df.head(10).copy()
        df['display'] = df['phone_number'].apply(lambda x: anonymize_contact(x, anonymize))

        # Create bars
        y_pos = np.arange(len(df))
        bars = ax.barh(y_pos, df['total_messages'], color=IMESSAGE_BLUE, alpha=0.8)

        # Customize
        ax.set_yticks(y_pos)
        ax.set_yticklabels(df['display'], color=TEXT_COLOR, fontsize=12)
        ax.invert_yaxis()
        ax.set_xlabel('Total Messages', color=TEXT_COLOR, fontsize=14)
        ax.set_title('Your Top Contacts', color=TEXT_COLOR, fontsize=24, fontweight='bold', pad=20)

        # Style
        ax.set_facecolor(BACKGROUND_COLOR)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(TEXT_COLOR)
        ax.spines['bottom'].set_color(TEXT_COLOR)
        ax.tick_params(colors=TEXT_COLOR)
        ax.grid(axis='x', alpha=0.2, color=TEXT_COLOR)

        # Add value labels
        for i, (idx, row) in enumerate(df.iterrows()):
            ax.text(row['total_messages'], i, f" {format_number(row['total_messages'])}",
                    va='center', color=TEXT_COLOR, fontsize=11, fontweight='bold')

        plt.tight_layout()
        plt.savefig(self.output_dir / filename, dpi=300, facecolor=BACKGROUND_COLOR,
                    bbox_inches='tight')
        plt.close()

    def create_time_heatmap(self, time_patterns: Dict, filename: str = "time_heatmap.png"):
        """
        Create hourly activity heatmap

        Args:
            time_patterns: Dictionary from get_time_patterns()
            filename: Output filename
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), facecolor=BACKGROUND_COLOR)

        # Hourly distribution
        hourly = time_patterns['hourly_data']
        hours = list(range(24))
        values = [hourly.get(h, 0) for h in hours]

        bars1 = ax1.bar(hours, values, color=IMESSAGE_BLUE, alpha=0.8)

        # Highlight peak hour
        peak_hour = time_patterns['most_active_hour']
        bars1[peak_hour].set_color(IMESSAGE_GREEN)

        ax1.set_xlabel('Hour of Day', color=TEXT_COLOR, fontsize=12)
        ax1.set_ylabel('Messages', color=TEXT_COLOR, fontsize=12)
        ax1.set_title('Messages by Hour', color=TEXT_COLOR, fontsize=18, fontweight='bold')
        ax1.set_xticks(hours)
        ax1.set_xticklabels([f'{h:02d}:00' if h % 3 == 0 else '' for h in hours])

        # Style
        ax1.set_facecolor(BACKGROUND_COLOR)
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.spines['left'].set_color(TEXT_COLOR)
        ax1.spines['bottom'].set_color(TEXT_COLOR)
        ax1.tick_params(colors=TEXT_COLOR)
        ax1.grid(axis='y', alpha=0.2, color=TEXT_COLOR)

        # Daily distribution
        daily = time_patterns['daily_data']
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        values = [daily.get(d, 0) for d in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']]

        bars2 = ax2.bar(days, values, color=ACCENT_COLOR, alpha=0.8)

        # Highlight peak day
        peak_idx = values.index(max(values))
        bars2[peak_idx].set_color(IMESSAGE_GREEN)

        ax2.set_xlabel('Day of Week', color=TEXT_COLOR, fontsize=12)
        ax2.set_ylabel('Messages', color=TEXT_COLOR, fontsize=12)
        ax2.set_title('Messages by Day', color=TEXT_COLOR, fontsize=18, fontweight='bold')

        # Style
        ax2.set_facecolor(BACKGROUND_COLOR)
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        ax2.spines['left'].set_color(TEXT_COLOR)
        ax2.spines['bottom'].set_color(TEXT_COLOR)
        ax2.tick_params(colors=TEXT_COLOR)
        ax2.grid(axis='y', alpha=0.2, color=TEXT_COLOR)

        plt.tight_layout()
        plt.savefig(self.output_dir / filename, dpi=300, facecolor=BACKGROUND_COLOR,
                    bbox_inches='tight')
        plt.close()

    def create_ghosting_report(self, ghosting_df: pd.DataFrame,
                                anonymize: bool = False,
                                filename: str = "ghosting.png"):
        """
        Create ghosting analysis chart

        Args:
            ghosting_df: DataFrame from get_ghosting_analysis()
            anonymize: Whether to anonymize
            filename: Output filename
        """
        if len(ghosting_df) == 0:
            return

        fig, ax = plt.subplots(figsize=(12, 8), facecolor=BACKGROUND_COLOR)

        # Prepare data
        df = ghosting_df.head(10).copy()
        df['display'] = df['phone_number'].apply(lambda x: anonymize_contact(x, anonymize))

        # Create bars
        y_pos = np.arange(len(df))
        bars = ax.barh(y_pos, df['response_rate'], color=IMESSAGE_BLUE, alpha=0.8)

        # Color bars by ghosting severity
        for i, rate in enumerate(df['response_rate']):
            if rate < 30:
                bars[i].set_color('#FF3B30')  # Red for severe ghosting
            elif rate < 50:
                bars[i].set_color('#FF9500')  # Orange for moderate
            else:
                bars[i].set_color(IMESSAGE_BLUE)

        # Customize
        ax.set_yticks(y_pos)
        ax.set_yticklabels(df['display'], color=TEXT_COLOR, fontsize=12)
        ax.invert_yaxis()
        ax.set_xlabel('Response Rate (%)', color=TEXT_COLOR, fontsize=14)
        ax.set_title('Who Ghosts You Most', color=TEXT_COLOR, fontsize=24, fontweight='bold', pad=20)
        ax.set_xlim(0, 100)

        # Style
        ax.set_facecolor(BACKGROUND_COLOR)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(TEXT_COLOR)
        ax.spines['bottom'].set_color(TEXT_COLOR)
        ax.tick_params(colors=TEXT_COLOR)
        ax.grid(axis='x', alpha=0.2, color=TEXT_COLOR)

        # Add value labels
        for i, (idx, row) in enumerate(df.iterrows()):
            ax.text(row['response_rate'], i, f" {row['response_rate']:.0f}%",
                    va='center', color=TEXT_COLOR, fontsize=11, fontweight='bold')

        plt.tight_layout()
        plt.savefig(self.output_dir / filename, dpi=300, facecolor=BACKGROUND_COLOR,
                    bbox_inches='tight')
        plt.close()

    def create_group_chat_leaderboard(self, groups_df: pd.DataFrame,
                                       filename: str = "group_chats.png"):
        """
        Create group chat activity leaderboard

        Args:
            groups_df: DataFrame from get_group_chat_stats()
            filename: Output filename
        """
        if len(groups_df) == 0:
            return

        fig, ax = plt.subplots(figsize=(12, 8), facecolor=BACKGROUND_COLOR)

        # Prepare data
        df = groups_df.head(10).copy()

        # Create bars
        y_pos = np.arange(len(df))
        bars = ax.barh(y_pos, df['total_messages'], color=IMESSAGE_GREEN, alpha=0.8)

        # Customize
        ax.set_yticks(y_pos)
        ax.set_yticklabels(df['chat_name'].str[:30], color=TEXT_COLOR, fontsize=12)
        ax.invert_yaxis()
        ax.set_xlabel('Total Messages', color=TEXT_COLOR, fontsize=14)
        ax.set_title('Most Active Group Chats', color=TEXT_COLOR, fontsize=24, fontweight='bold', pad=20)

        # Style
        ax.set_facecolor(BACKGROUND_COLOR)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(TEXT_COLOR)
        ax.spines['bottom'].set_color(TEXT_COLOR)
        ax.tick_params(colors=TEXT_COLOR)
        ax.grid(axis='x', alpha=0.2, color=TEXT_COLOR)

        # Add value labels
        for i, (idx, row) in enumerate(df.iterrows()):
            ax.text(row['total_messages'], i,
                    f" {format_number(row['total_messages'])} ({row['your_participation_pct']:.0f}% you)",
                    va='center', color=TEXT_COLOR, fontsize=10, fontweight='bold')

        plt.tight_layout()
        plt.savefig(self.output_dir / filename, dpi=300, facecolor=BACKGROUND_COLOR,
                    bbox_inches='tight')
        plt.close()

    def create_personality_card(self, personality: Dict, stats: Dict,
                                 filename: str = "personality.png"):
        """
        Create messaging personality card

        Args:
            personality: Dictionary from get_messaging_personality()
            stats: Summary stats
            filename: Output filename
        """
        fig = plt.figure(figsize=(10, 12), facecolor=BACKGROUND_COLOR)

        ax = fig.add_subplot(111)
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 12)
        ax.axis('off')

        # Title
        ax.text(5, 11, 'Your Texting Personality', ha='center', va='top',
                fontsize=40, fontweight='bold', color=TEXT_COLOR)

        # Personality traits
        y_pos = 9.5
        traits = [
            ('Time', personality['time_personality'], IMESSAGE_BLUE),
            ('Style', personality['length_personality'], IMESSAGE_GREEN),
            ('Emojis', personality['emoji_personality'], ACCENT_COLOR),
            ('Social', personality['initiation_personality'], '#FF9500'),
        ]

        for category, trait, color in traits:
            ax.text(5, y_pos, trait, ha='center', va='center',
                    fontsize=36, fontweight='bold', color=color)
            ax.text(5, y_pos - 0.5, category, ha='center', va='center',
                    fontsize=18, color=TEXT_COLOR, alpha=0.6)
            y_pos -= 2.2

        # Additional stats
        ax.text(5, 1.5, f"Peak Hour: {personality['peak_hour']:02d}:00", ha='center',
                fontsize=16, color=TEXT_COLOR, alpha=0.7)

        ax.text(5, 0.5, 'Based on your messaging patterns', ha='center',
                fontsize=14, color=TEXT_COLOR, alpha=0.5)

        plt.tight_layout()
        plt.savefig(self.output_dir / filename, dpi=300, facecolor=BACKGROUND_COLOR,
                    bbox_inches='tight', pad_inches=0.3)
        plt.close()

    def create_fastest_responders_chart(self, responders_df: pd.DataFrame,
                                         anonymize: bool = False,
                                         filename: str = "fast_responders.png"):
        """
        Create fastest responders chart

        Args:
            responders_df: DataFrame from get_fastest_responders()
            anonymize: Whether to anonymize
            filename: Output filename
        """
        if len(responders_df) == 0:
            return

        fig, ax = plt.subplots(figsize=(12, 8), facecolor=BACKGROUND_COLOR)

        # Prepare data
        df = responders_df.head(10).copy()
        df['display'] = df['phone_number'].apply(lambda x: anonymize_contact(x, anonymize))
        df['display_time'] = df['median_response_minutes'].apply(format_duration)

        # Create bars
        y_pos = np.arange(len(df))
        bars = ax.barh(y_pos, df['median_response_minutes'], color=IMESSAGE_GREEN, alpha=0.8)

        # Customize
        ax.set_yticks(y_pos)
        ax.set_yticklabels(df['display'], color=TEXT_COLOR, fontsize=12)
        ax.invert_yaxis()
        ax.set_xlabel('Median Response Time', color=TEXT_COLOR, fontsize=14)
        ax.set_title('Fastest Responders', color=TEXT_COLOR, fontsize=24, fontweight='bold', pad=20)

        # Style
        ax.set_facecolor(BACKGROUND_COLOR)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(TEXT_COLOR)
        ax.spines['bottom'].set_color(TEXT_COLOR)
        ax.tick_params(colors=TEXT_COLOR)
        ax.grid(axis='x', alpha=0.2, color=TEXT_COLOR)

        # Add value labels
        for i, (idx, row) in enumerate(df.iterrows()):
            ax.text(row['median_response_minutes'], i, f" {row['display_time']}",
                    va='center', color=TEXT_COLOR, fontsize=11, fontweight='bold')

        plt.tight_layout()
        plt.savefig(self.output_dir / filename, dpi=300, facecolor=BACKGROUND_COLOR,
                    bbox_inches='tight')
        plt.close()

    def generate_all_images(self, analyzer, period: str, anonymize: bool = False):
        """
        Generate all visualization images

        Args:
            analyzer: MessageAnalyzer instance
            period: "Past Year" or "All Time"
            anonymize: Whether to anonymize contacts
        """
        print("Generating visualizations...")

        # Summary
        stats = analyzer.get_summary_stats()
        self.create_summary_card(stats, period)
        print("✓ Summary card")

        # Top contacts
        contacts = analyzer.get_top_contacts()
        if len(contacts) > 0:
            self.create_top_contacts_chart(contacts, anonymize)
            print("✓ Top contacts")

        # Time patterns
        time_patterns = analyzer.get_time_patterns()
        self.create_time_heatmap(time_patterns)
        print("✓ Time heatmap")

        # Ghosting
        ghosting = analyzer.get_ghosting_analysis()
        if len(ghosting) > 0:
            self.create_ghosting_report(ghosting, anonymize)
            print("✓ Ghosting report")

        # Fastest responders
        responders = analyzer.get_fastest_responders()
        if len(responders) > 0:
            self.create_fastest_responders_chart(responders, anonymize)
            print("✓ Fastest responders")

        # Group chats
        groups = analyzer.get_group_chat_stats()
        if len(groups) > 0:
            self.create_group_chat_leaderboard(groups)
            print("✓ Group chats")

        # Personality
        personality = analyzer.get_messaging_personality()
        self.create_personality_card(personality, stats)
        print("✓ Personality card")

        print(f"\nAll visualizations saved to: {self.output_dir.absolute()}")
