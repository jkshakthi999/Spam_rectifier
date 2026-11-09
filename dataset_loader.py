"""
Module 1: Email Dataset Loading
Downloads, extracts, parses, and loads email/SMS datasets:
- SMS Spam Collection Dataset (UCI Repository)
- Apache SpamAssassin Public Corpus (RFC 822 emails)
- Modern Email / SMS Curated Samples (lottery, phishing, KYC scams, business emails)
"""

import os
import sys
import io
import tarfile
import zipfile
import email
from email import policy
from email.parser import BytesParser
import urllib.request
import pandas as pd

# Safe console encoding for Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

UCI_SMS_URL = "https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip"
SPAMASSASSIN_SPAM_URL = "https://spamassassin.apache.org/old/publiccorpus/20030228_spam.tar.bz2"
SPAMASSASSIN_HAM_URL = "https://spamassassin.apache.org/old/publiccorpus/20030228_easy_ham.tar.bz2"

DEFAULT_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
DEFAULT_DATASET_CSV = os.path.join(DEFAULT_DATA_DIR, "spam_dataset.csv")

# Representative modern & financial spam/ham samples to augment older corpus
CURATED_SUPPLEMENT = [
    # Indian / Global modern financial spam samples
    ("spam", "Congratulations! You won ₹10 lakh in lottery. Call now or click to claim cash prize!"),
    ("spam", "Dear customer, you have won ₹50,00,000 in Diwali bumper draw! Claim reward by sending your bank details."),
    ("spam", "URGENT: Your SBI account has been suspended due to pending KYC. Click http://sbi-kyc-update.xyz to verify immediately!"),
    ("spam", "Congratulations! You have been selected for a pre-approved personal loan of ₹15,00,000 at zero interest. Apply today!"),
    ("spam", "Win guaranteed ₹25,000 daily working from home 2 hours. Join WhatsApp group now http://easy-money-india.net"),
    ("spam", "Alert: Cash reward of ₹5,00,000 credited to your wallet. Click link to transfer to your bank account before expiry."),
    ("spam", "Dear user, you won ₹1 Crore KBC lottery jackpot. Contact manager on WhatsApp +919876543210 to claim."),
    ("spam", "Exclusive deal! Claim your FREE iPhone 15 Pro and ₹5000 Amazon gift voucher today. Limited slots left!"),
    ("spam", "FINAL NOTICE: Claim your tax refund of ₹48,200 immediately by verifying PAN and OTP at http://incometax-refunds.com"),
    ("spam", "Hot singles in your area want to chat! Meet verified women near you for free tonight. Click here."),
    ("spam", "Crypto opportunity: Invest $100 and receive $10,000 within 24 hours guaranteed return! Zero risk trading."),
    ("spam", "Your Netflix membership has expired. Update billing card details now to avoid permanent cancellation: http://netflix-renew.net"),
    ("spam", "Inheritance transfer of $12.5M USD from late diplomat. Please reply with full name and address for wire release."),
    ("spam", "Discount Pharmacy: Buy Viagra, Cialis and Xanax online without prescription. 80% discount and discreet overnight delivery."),
    ("spam", "Act now! Claim your free £1000 shopping card at Tesco. Text WIN to 88010 now."),
    ("spam", "You are the selected winner of our weekly prize draw! Claim your ₹2 lakh reward immediately by clicking the link."),

    # Real ham samples
    ("ham", "Hi Shakthi, could you please review the attached project report and share your feedback before our 4 PM meeting?"),
    ("ham", "Your OTP for transaction of ₹1,500 at Amazon is 492810. Do not share this OTP with anyone, including bank officials."),
    ("ham", "Hi team, the sprint demo is scheduled for tomorrow at 11:00 AM. Please make sure your PRs are merged."),
    ("ham", "Dear customer, your electricity bill of ₹2,340 for the month of October is due on 15th Nov. Thank you for paying on time."),
    ("ham", "Dear customer, your electricity bill of ₹1,420 has been generated. The due date for payment is November 18."),
    ("ham", "Your water utility bill of ₹450 is ready for payment. Log in to portal to download the receipt."),
    ("ham", "Dear customer, your broadband bill of ₹899 has been generated. Auto-debit will occur on 5th."),
    ("ham", "Can we reschedule our lunch to 1:30 PM? I am caught in a customer support call right now."),
    ("ham", "Your order #405-928172 has been dispatched and will arrive by tomorrow evening via BlueDart courier."),
    ("ham", "Your Amazon order #402-91823 has been shipped and is out for delivery today with tracking number BLR71829."),
    ("ham", "Please find the meeting minutes from today's discussion on the machine learning spam classification pipeline."),
    ("ham", "Hey, are you free this weekend? Let's catch up for coffee and discuss the semester exams."),
    ("ham", "Your flight 6E-204 from Bangalore to Delhi is confirmed. Web check-in opens 48 hours before departure."),
    ("ham", "Attached is the revised invoice for the consulting services rendered in September. Let me know if any questions."),
    ("ham", "Your monthly bank account statement for account ending in 4102 is available for download."),
    ("ham", "Your OTP for login to your HDFC NetBanking is 739102. Valid for 5 minutes. Do not share this OTP with anyone."),
    ("ham", "Salary for the month of October ₹85,000 has been credited to your savings account ending in 9812."),
    ("ham", "Your monthly subscription receipt for GitHub Pro of $4.00 has been paid successfully."),
    ("ham", "Thank you for shopping at D-Mart. Your bill total is ₹3,210. Visit again!"),
    ("ham", "Your train PNR 4829104829 is confirmed. Coach B3, Berth 24. Departure 20:45 from MGR Chennai Central."),
    ("ham", "Your Uber ride with driver Ramesh is arriving in 3 mins. OTP is 4182."),
    ("ham", "Reminder: Dental check-up appointment tomorrow at 11:30 AM with Dr. Sharma."),
    ("ham", "Assignment submission deadline for Machine Learning has been extended to Monday 11:59 PM.")
]


class DatasetLoader:
    """
    Handles fetching, extraction, curation, and loading of datasets.
    """

    def __init__(self, data_dir: str = DEFAULT_DATA_DIR):
        self.data_dir = data_dir
        self.raw_dir = os.path.join(data_dir, "raw")
        os.makedirs(self.raw_dir, exist_ok=True)

    def fetch_uci_sms_data(self) -> pd.DataFrame:
        """
        Downloads and parses the UCI SMS Spam Collection dataset.
        Contains 5,574 labeled SMS messages.
        """
        sms_file_path = os.path.join(self.raw_dir, "SMSSpamCollection")
        if not os.path.exists(sms_file_path):
            print(f"[DatasetLoader] Downloading UCI SMS Spam Collection from {UCI_SMS_URL}...")
            req = urllib.request.Request(UCI_SMS_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                content = resp.read()
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                z.extractall(self.raw_dir)
            print("[DatasetLoader] UCI SMS Spam Collection downloaded and extracted.")

        # Read tab-separated file
        df = pd.read_csv(
            sms_file_path,
            sep="\t",
            names=["label", "text"],
            encoding="utf-8",
            on_bad_lines="skip"
        )
        df["label"] = df["label"].astype(str).str.strip().str.lower()
        df["text"] = df["text"].astype(str).str.strip()
        df = df[df["label"].isin(["ham", "spam"])]
        print(f"[DatasetLoader] Loaded {len(df)} samples from UCI SMS dataset.")
        return df

    @staticmethod
    def _parse_email_file(raw_bytes: bytes) -> str:
        """Parses an RFC 822 email file into a cleaned Subject + Body string."""
        try:
            msg = BytesParser(policy=policy.default).parsebytes(raw_bytes)
            subject = msg.get("subject", "") or ""
            
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disp = str(part.get("Content-Disposition"))
                    if content_type == "text/plain" and "attachment" not in content_disp:
                        try:
                            body += part.get_payload(decode=True).decode(errors="ignore") + " "
                        except Exception:
                            pass
            else:
                try:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body = payload.decode(errors="ignore")
                    else:
                        body = str(msg.get_payload())
                except Exception:
                    body = str(msg.get_payload())
            
            full_text = f"{subject} {body}".strip()
            return full_text
        except Exception:
            return ""

    def fetch_spamassassin_subset(self, max_samples: int = 500) -> pd.DataFrame:
        """
        Downloads a curated subset of SpamAssassin public corpus.
        Extracts real email headers and bodies.
        """
        records = []
        targets = [
            ("spam", SPAMASSASSIN_SPAM_URL, "20030228_spam.tar.bz2"),
            ("ham", SPAMASSASSIN_HAM_URL, "20030228_easy_ham.tar.bz2")
        ]

        for label, url, filename in targets:
            dest_file = os.path.join(self.raw_dir, filename)
            try:
                if not os.path.exists(dest_file):
                    print(f"[DatasetLoader] Downloading SpamAssassin ({label}) from {url}...")
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=45) as resp:
                        with open(dest_file, "wb") as f:
                            f.write(resp.read())
                    print(f"[DatasetLoader] Saved {filename}.")

                count = 0
                with tarfile.open(dest_file, "r:bz2") as tar:
                    for member in tar.getmembers():
                        if member.isfile() and not member.name.endswith(".cmds"):
                            f = tar.extractfile(member)
                            if f:
                                email_text = self._parse_email_file(f.read())
                                if len(email_text) > 20:
                                    records.append({"label": label, "text": email_text})
                                    count += 1
                                    if count >= max_samples:
                                        break
                print(f"[DatasetLoader] Extracted {count} {label} emails from SpamAssassin {filename}.")
            except Exception as e:
                print(f"[DatasetLoader] Note: Could not load SpamAssassin archive ({filename}): {e}. Continuing.")

        if records:
            return pd.DataFrame(records)
        return pd.DataFrame(columns=["label", "text"])

    def build_unified_dataset(self, save_path: str = DEFAULT_DATASET_CSV, force_rebuild: bool = False) -> pd.DataFrame:
        """
        Builds the unified comprehensive dataset:
        1. SMS Spam Collection (5500+ items)
        2. SpamAssassin email samples
        3. Modern financial and phishing curated cases
        """
        if os.path.exists(save_path) and not force_rebuild:
            print(f"[DatasetLoader] Loading existing dataset from {save_path}...")
            df = pd.read_csv(save_path, encoding="utf-8")
            print(f"[DatasetLoader] Dataset ready with {len(df)} samples ({df['label'].value_counts().to_dict()}).")
            return df

        frames = []

        # 1. UCI SMS dataset
        try:
            sms_df = self.fetch_uci_sms_data()
            frames.append(sms_df)
        except Exception as e:
            print(f"[DatasetLoader] Warning: Failed to load UCI SMS dataset: {e}")

        # 2. SpamAssassin email dataset
        try:
            sa_df = self.fetch_spamassassin_subset(max_samples=400)
            if not sa_df.empty:
                frames.append(sa_df)
        except Exception as e:
            print(f"[DatasetLoader] Warning: Failed to load SpamAssassin dataset: {e}")

        # 3. Modern curated supplement
        supp_df = pd.DataFrame(CURATED_SUPPLEMENT, columns=["label", "text"])
        frames.append(supp_df)

        if not frames:
            raise RuntimeError("Failed to load any dataset source!")

        unified_df = pd.concat(frames, ignore_index=True)
        unified_df = unified_df.drop_duplicates(subset=["text"])
        unified_df = unified_df.dropna(subset=["text", "label"])
        unified_df = unified_df[unified_df["text"].str.strip().str.len() > 5]

        # Save to disk
        unified_df.to_csv(save_path, index=False, encoding="utf-8")
        print(f"[DatasetLoader] Unified dataset built successfully and saved to {save_path}.")
        print(f"[DatasetLoader] Total samples: {len(unified_df)} -> {unified_df['label'].value_counts().to_dict()}")
        return unified_df

    def load_dataset(self, csv_path: str = DEFAULT_DATASET_CSV) -> pd.DataFrame:
        """Loads dataset, building it if not already present."""
        if not os.path.exists(csv_path):
            return self.build_unified_dataset(save_path=csv_path)
        return pd.read_csv(csv_path, encoding="utf-8")


if __name__ == "__main__":
    loader = DatasetLoader()
    df = loader.build_unified_dataset()
    print("Dataset Head:")
    print(df.head())
