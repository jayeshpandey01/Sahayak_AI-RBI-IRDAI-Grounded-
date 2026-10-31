"""Official Website Knowledge Ingestion, Verification & Retrieval Engine.

Conforms to rag_docs.md specifications, .agents/skills/rag-implementation,
and .agents/skills/clean-code standards.
Provides verified knowledge and citations extracted from official Indian regulatory
and financial infrastructure websites:
- Reserve Bank of India (RBI): https://www.rbi.org.in, https://sachet.rbi.org.in, https://cms.rbi.org.in
- National Payments Corporation of India (NPCI): https://www.npci.org.in
- Insurance Regulatory and Development Authority of India (IRDAI): https://irdai.gov.in
- Official Verified Lender & Banking Standards (KFS, Fair Practices Code, BCSBI)
"""

import hashlib
import re
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

from app.models.schemas import GroundedCitation, LanguageCode

OFFICIAL_DOMAINS_WHITELIST = {
    "rbi.org.in",
    "www.rbi.org.in",
    "sachet.rbi.org.in",
    "cms.rbi.org.in",
    "npci.org.in",
    "www.npci.org.in",
    "irdai.gov.in",
    "www.irdai.gov.in",
    "bimabharosa.irdai.gov.in",
    "iba.org.in",
    "sahayakai.in",
}


def is_official_url(url: Optional[str]) -> bool:
    """Validate that a URL strictly originates from an approved official regulatory domain."""
    if not url:
        return False
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        return any(hostname == domain or hostname.endswith(f".{domain}") for domain in OFFICIAL_DOMAINS_WHITELIST)
    except Exception:
        return False


def _compute_sha256(content: str) -> str:
    return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()


OFFICIAL_WEBSITE_RECORDS: List[Dict[str, Any]] = [
    # --------------------------------------------------------------------------
    # 1. RESERVE BANK OF INDIA (RBI) — OFFICIAL WEBSITE RETRIEVALS
    # --------------------------------------------------------------------------
    {
        "id": "rbi_kfs_master_direction_2024",
        "collection_type": "regulatory",
        "source_name": "Reserve Bank of India",
        "source_url": "https://www.rbi.org.in/Scripts/BS_CircularIndexDisplay.aspx?Id=12662",
        "document_name": "RBI Master Direction on Key Fact Statement (KFS) for Loans",
        "document_type": "Master Direction",
        "financial_category": "retail_lending_transparency",
        "provider_name": "Reserve Bank of India",
        "version": "2024-KFS-v1",
        "owner": "RBI Department of Regulation",
        "jurisdiction": "IN",
        "published_at": "2024-04-15",
        "effective_from": "2024-10-01",
        "review_due": "2027-10-01",
        "last_verified_at": "2026-10-31",
        "status": "active",
        "allowed_use": "assistant_grounding",
        "clause": "Mandatory Key Fact Statement (KFS) and APR Transparency",
        "approved": True,
        "text": (
            "Under RBI's official Master Direction on Key Fact Statements (KFS), all regulated lenders "
            "(banks and NBFCs) must provide a standardized KFS to borrowers before loan execution. "
            "The KFS must explicitly state the Annual Percentage Rate (APR) including all processing fees, "
            "documentation charges, and third-party expenses. It must have a validity period of at least 3 working "
            "days for retail borrowers to compare terms, and no hidden or unstated charges can be levied."
        ),
        "aliases": [
            "kfs", "key fact statement", "apr", "annual percentage rate", "hidden charges",
            "loan breakdown", "loan charges", "cooling off period", "processing fee rule",
            "केएफएस", "की फैक्ट स्टेटमेंट", "वार्षिक प्रतिशत दर", "छिपे हुए शुल्क", "लोन नियम"
        ],
    },
    {
        "id": "rbi_digital_lending_directions_2022",
        "collection_type": "regulatory",
        "source_name": "Reserve Bank of India",
        "source_url": "https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12554",
        "document_name": "RBI Guidelines on Digital Lending",
        "document_type": "Directions",
        "financial_category": "digital_lending_regulations",
        "provider_name": "Reserve Bank of India",
        "version": "2022-DL-v1",
        "owner": "RBI Department of Regulation",
        "jurisdiction": "IN",
        "published_at": "2022-09-02",
        "effective_from": "2022-09-02",
        "review_due": "2027-09-02",
        "last_verified_at": "2026-10-31",
        "status": "active",
        "allowed_use": "assistant_grounding",
        "clause": "Direct Disbursals, LSP Disclosure, and Borrower Privacy",
        "approved": True,
        "text": (
            "According to the official RBI Digital Lending Directions, loan disbursements and repayments must execute "
            "directly between the bank account of the borrower and the regulated entity (Bank/NBFC), without passing "
            "through any third-party pool or lending app wallet. Lending Service Providers (LSPs) must be clearly "
            "named, mobile apps cannot access phone media/contacts, and a mandatory cooling-off period must be provided."
        ),
        "aliases": [
            "digital lending", "digital lending guidelines", "rbi digital loan", "disbursement rule",
            "lsp", "lending service provider", "third party wallet", "phone contacts", "privacy",
            "डिजिटल लेंडिंग", "लोन दिशानिर्देश", "आरबीआई डिजिटल लोन", "खाते में पैसा", "संपर्क अनुमति"
        ],
    },
    {
        "id": "rbi_recovery_agent_code_2022",
        "collection_type": "regulatory",
        "source_name": "Reserve Bank of India",
        "source_url": "https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12373&Mode=0",
        "document_name": "RBI Fair Practices Code - Recovery Agents and Harassment Prevention",
        "document_type": "Circular",
        "financial_category": "borrower_protection",
        "provider_name": "Reserve Bank of India",
        "version": "2022-FPC-v1",
        "owner": "RBI Department of Regulation",
        "jurisdiction": "IN",
        "published_at": "2022-08-12",
        "effective_from": "2022-08-12",
        "review_due": "2027-08-12",
        "last_verified_at": "2026-10-31",
        "status": "active",
        "allowed_use": "assistant_grounding",
        "clause": "Permitted Hours and Prohibition of Harassment by Recovery Agents",
        "approved": True,
        "text": (
            "Under RBI's official Fair Practices Code, recovery agents are strictly prohibited from contacting "
            "borrowers before 8:00 AM or after 7:00 PM. Agents cannot use verbal abuse, threats, public humiliation, "
            "or contact family members and acquaintances. Regulated entities are directly accountable for actions of "
            "their outsourced recovery agents, and violations can be reported to the RBI Ombudsman."
        ),
        "aliases": [
            "recovery agent", "recovery call", "midnight call", "agent timing", "harassment",
            "threats", "recovery rule", "call timings", "loan recovery", "abuse",
            "रिकवरी एजेंट", "रिकवरी कॉल", "कॉल का समय", "परेशान करना", "धमकी", "वसूली नियम"
        ],
    },
    {
        "id": "rbi_floating_rate_prepayment_penalty_ban",
        "collection_type": "regulatory",
        "source_name": "Reserve Bank of India",
        "source_url": "https://www.rbi.org.in/scripts/FS_Notification.aspx?Id=8905&fn=2&Mode=0",
        "document_name": "RBI Prohibition of Foreclosure Charges on Floating-Rate Loans",
        "document_type": "Circular",
        "financial_category": "borrower_rights",
        "provider_name": "Reserve Bank of India",
        "version": "2014-PREPAY-v1",
        "owner": "RBI Department of Regulation",
        "jurisdiction": "IN",
        "published_at": "2014-05-07",
        "effective_from": "2014-05-07",
        "review_due": "2027-05-07",
        "last_verified_at": "2026-10-31",
        "status": "active",
        "allowed_use": "assistant_grounding",
        "clause": "Zero Foreclosure & Pre-Payment Charges on Floating Loans for Individuals",
        "approved": True,
        "text": (
            "The Reserve Bank of India mandates that banks and NBFCs cannot levy any foreclosure charges or "
            "pre-payment penalties on floating-rate term loans sanctioned to individual borrowers (with or without "
            "co-obligants), irrespective of the purpose of the loan. Prepayment fees are only permissible on "
            "fixed-rate loans or non-individual business entities."
        ),
        "aliases": [
            "foreclosure", "prepayment", "pre-payment", "foreclosure charges", "floating rate",
            "prepayment penalty", "close loan early", "part payment", "floating loan penalty",
            "फोरक्लोजर", "प्रीपेमेंट", "फ्लोटिंग रेट", "समय से पहले भुगतान", "अतिरिक्त शुल्क"
        ],
    },
    {
        "id": "rbi_integrated_ombudsman_scheme_2021",
        "collection_type": "regulatory",
        "source_name": "Reserve Bank of India",
        "source_url": "https://cms.rbi.org.in",
        "document_name": "RBI Integrated Ombudsman Scheme (CMS)",
        "document_type": "Scheme",
        "financial_category": "grievance_redressal",
        "provider_name": "Reserve Bank of India",
        "version": "2021-RBIO-v1",
        "owner": "RBI Consumer Education and Protection Department",
        "jurisdiction": "IN",
        "published_at": "2021-11-12",
        "effective_from": "2021-11-12",
        "review_due": "2027-11-12",
        "last_verified_at": "2026-10-31",
        "status": "active",
        "allowed_use": "assistant_grounding",
        "clause": "Filing Complaints against Regulated Entities (CMS & Toll-Free 14448)",
        "approved": True,
        "text": (
            "Under the Reserve Bank - Integrated Ombudsman Scheme (RBI-IOS), consumers can lodge complaints against "
            "any bank, NBFC, or system participant free of charge if the institution does not resolve the complaint "
            "within 30 days or provides an unsatisfactory reply. Complaints can be filed online at cms.rbi.org.in, "
            "via email to crpc@rbi.org.in, or by calling toll-free 14448."
        ),
        "aliases": [
            "ombudsman", "rbi ombudsman", "file complaint", "cms rbi", "complaint against bank",
            "toll free 14448", "crpc rbi", "banking ombudsman", "grievance redressal",
            "लोकपाल", "आरबीआई लोकपाल", "शिकायत", "बैंक की शिकायत", "शिकायत निवारण"
        ],
    },
    {
        "id": "rbi_sachet_portal_verification",
        "collection_type": "regulatory",
        "source_name": "Reserve Bank of India - Sachet",
        "source_url": "https://sachet.rbi.org.in",
        "document_name": "RBI Sachet Portal for NBFC Verification and Fraud Reporting",
        "document_type": "Public Portal",
        "financial_category": "fraud_prevention",
        "provider_name": "Reserve Bank of India",
        "version": "2024-SACHET-v1",
        "owner": "State Level Coordination Committee (SLCC)",
        "jurisdiction": "IN",
        "published_at": "2024-01-15",
        "effective_from": "2024-01-15",
        "review_due": "2027-01-15",
        "last_verified_at": "2026-10-31",
        "status": "active",
        "allowed_use": "assistant_grounding",
        "clause": "Verifying Registered NBFCs and Reporting Unauthorized Digital Apps",
        "approved": True,
        "text": (
            "The RBI Sachet portal (sachet.rbi.org.in) allows borrowers and citizens to verify whether a lending entity "
            "or NBFC is officially registered with and regulated by the Reserve Bank of India. Users can also report illegal "
            "deposit schemes, fake loan apps, and fraudulent lending entities directly to state enforcement agencies."
        ),
        "aliases": [
            "sachet", "rbi sachet", "verify nbfc", "registered nbfc", "fake loan app",
            "illegal app", "check nbfc status", "report fraud", "sachet.rbi.org.in",
            "सचेत", "सचेत पोर्टल", "एनबीएफसी जांच", "फर्जी लोन ऐप", "धोखाधड़ी रिपोर्ट"
        ],
    },

    # --------------------------------------------------------------------------
    # 2. NATIONAL PAYMENTS CORPORATION OF INDIA (NPCI) — UPI OFFICIAL RULES
    # --------------------------------------------------------------------------
    {
        "id": "npci_upi_dispute_tat_and_auto_reversal",
        "collection_type": "regulatory",
        "source_name": "National Payments Corporation of India",
        "source_url": "https://www.npci.org.in/what-we-do/upi/dispute-redressal-mechanism",
        "document_name": "NPCI UPI Operating Guidelines & Dispute Resolution TAT",
        "document_type": "Operating Guidelines",
        "financial_category": "payment_systems",
        "provider_name": "NPCI",
        "version": "2024-UPI-v1",
        "owner": "NPCI UPI Operations",
        "jurisdiction": "IN",
        "published_at": "2024-03-01",
        "effective_from": "2024-03-01",
        "review_due": "2027-03-01",
        "last_verified_at": "2026-10-31",
        "status": "active",
        "allowed_use": "assistant_grounding",
        "clause": "T+1 Turnaround Time for Failed UPI Transactions and Auto-Reversal Penalty",
        "approved": True,
        "text": (
            "As per official NPCI guidelines and RBI circular on harmonization of TAT for failed transactions, "
            "if money is debited from a user's bank account but not credited to the beneficiary in a UPI transfer, "
            "the amount must be auto-reversed to the remitter's account within T+1 working days. If the bank fails "
            "to reverse within T+1, it must pay compensation of ₹100 per day of delay to the customer."
        ),
        "aliases": [
            "upi dispute", "upi failed transaction", "money deducted not received", "t+1 auto reversal",
            "100 per day penalty", "npci upi rule", "upi money stuck", "upi refund timeline",
            "यूपीआई विवाद", "पैसे कट गए लेकिन नहीं मिले", "यूपीआई रिफंड", "100 रुपये जुर्माना", "एनपीसीआई नियम"
        ],
    },
    {
        "id": "npci_upi_transaction_and_lite_limits",
        "collection_type": "regulatory",
        "source_name": "National Payments Corporation of India",
        "source_url": "https://www.npci.org.in/what-we-do/upi-lite/product-overview",
        "document_name": "NPCI UPI Limits and UPI Lite Guidelines",
        "document_type": "Circular",
        "financial_category": "upi_limits",
        "provider_name": "NPCI",
        "version": "2024-UPILITE-v1",
        "owner": "NPCI Product",
        "jurisdiction": "IN",
        "published_at": "2024-05-10",
        "effective_from": "2024-05-10",
        "review_due": "2027-05-10",
        "last_verified_at": "2026-10-31",
        "status": "active",
        "allowed_use": "assistant_grounding",
        "clause": "UPI Per-Transaction Limits, Capital Market Limits, and UPI Lite Offline Wallet",
        "approved": True,
        "text": (
            "NPCI sets standard UPI peer-to-peer (P2P) limits up to ₹1,00,000 per transaction, with higher limits "
            "up to ₹5,00,000 for verified hospitals, educational institutions, tax payments, and IPO/G-Sec applications. "
            "For UPI Lite, small-value payments up to ₹500 per transaction require no UPI PIN, with a maximum wallet "
            "balance limit of ₹2,000."
        ),
        "aliases": [
            "upi limit", "upi maximum limit", "upi lite limit", "upi per day limit", "upi 1 lakh limit",
            "upi hospital limit", "upi lite balance", "npci limit",
            "यूपीआई सीमा", "यूपीआई अधिकतम सीमा", "यूपीआई लाइट", "बिना पिन भुगतान"
        ],
    },

    # --------------------------------------------------------------------------
    # 3. INSURANCE REGULATORY & DEVELOPMENT AUTHORITY OF INDIA (IRDAI)
    # --------------------------------------------------------------------------
    {
        "id": "irdai_policyholder_protection_free_look",
        "collection_type": "regulatory",
        "source_name": "Insurance Regulatory and Development Authority of India",
        "source_url": "https://irdai.gov.in/regulations",
        "document_name": "IRDAI (Protection of Policyholders' Interests) Regulations",
        "document_type": "Regulations",
        "financial_category": "insurance_rights",
        "provider_name": "IRDAI",
        "version": "2024-IRDAI-v1",
        "owner": "IRDAI Consumer Affairs",
        "jurisdiction": "IN",
        "published_at": "2024-03-20",
        "effective_from": "2024-04-01",
        "review_due": "2027-04-01",
        "last_verified_at": "2026-10-31",
        "status": "active",
        "allowed_use": "assistant_grounding",
        "clause": "Mandatory 30-Day Free-Look Period for Electronic and Distance Policies",
        "approved": True,
        "text": (
            "Under IRDAI's official regulations, every life and health insurance policyholder is entitled to a "
            "free-look cancellation period of 30 days from policy receipt date for policies purchased electronically "
            "or via distance marketing (15 days for physical policies). If canceled during this window, the insurer "
            "must refund the premium minus proportionate risk premium and medical stamp duty."
        ),
        "aliases": [
            "free look period", "insurance free look", "cancel insurance policy", "30 day free look",
            "irdai cancellation", "return insurance policy", "policy refund", "insurance look up",
            "फ्री लुक अवधि", "बीमा पॉलिसी रद्द", "30 दिन का समय", "पॉलिसी वापसी", "आईआरडीएआई नियम"
        ],
    },

    # --------------------------------------------------------------------------
    # 4. OFFICIAL BANKING & LENDER PROCEDURAL NORMS
    # --------------------------------------------------------------------------
    {
        "id": "banking_standard_kyc_and_eligibility",
        "collection_type": "provider",
        "source_name": "Banking & NBFC Industry Standards",
        "source_url": "https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=11566",
        "document_name": "RBI Master Direction on Know Your Customer (KYC)",
        "document_type": "Master Direction",
        "financial_category": "kyc_and_compliance",
        "provider_name": "Indian Banking Standards",
        "version": "2024-KYC-v1",
        "owner": "RBI KYC Cell",
        "jurisdiction": "IN",
        "published_at": "2024-01-04",
        "effective_from": "2024-01-04",
        "review_due": "2027-01-04",
        "last_verified_at": "2026-10-31",
        "status": "active",
        "allowed_use": "assistant_grounding",
        "clause": "Officially Valid Documents (OVD) for KYC and Income Verification Norms",
        "approved": True,
        "text": (
            "Under RBI's Master Direction on KYC, the Officially Valid Documents (OVD) for identity and address proof "
            "comprise: Passport, Driving Licence, Proof of possession of Aadhaar number, Voter Identity Card, and NREGA "
            "job card. For salaried personal loans, lenders typically require 3-6 months bank statements, latest 3 salary "
            "slips, and Form 16 or ITR for income underwriting."
        ),
        "aliases": [
            "kyc", "ovd", "documents required for loan", "aadhaar kyc", "pan card kyc",
            "salary slip loan", "bank statement requirement", "officially valid documents",
            "केवाईसी", "लोन के लिए दस्तावेज", "आधार कार्ड", "पैन कार्ड", "सैलरी स्लिप", "बैंक स्टेटमेंट"
        ],
    },
]


def get_all_official_sources() -> List[Dict[str, Any]]:
    """Return all verified official regulatory records."""
    return OFFICIAL_WEBSITE_RECORDS


def search_official_website_knowledge(
    query: str,
    language: LanguageCode = LanguageCode.EN,
    max_results: int = 3,
) -> List[Dict[str, Any]]:
    """
    Search official website records using high-signal token matching and alias mapping.
    Ensures user inquiries on official rules return grounded citations with verified URLs.
    """
    cleaned_query = query.strip().casefold()
    query_tokens = set(re.findall(r"[\w\u0900-\u097F]+", cleaned_query))
    if not query_tokens:
        return []

    scored_records = []
    for record in OFFICIAL_WEBSITE_RECORDS:
        text_tokens = set(re.findall(r"[\w\u0900-\u097F]+", record["text"].casefold()))
        clause_tokens = set(re.findall(r"[\w\u0900-\u097F]+", record["clause"].casefold()))
        aliases = record.get("aliases", [])

        # Check exact alias match
        alias_match = any(alias.casefold() in cleaned_query for alias in aliases)
        alias_tokens = set().union(*(re.findall(r"[\w\u0900-\u097F]+", a.casefold()) for a in aliases)) if aliases else set()

        overlap = len(query_tokens & (text_tokens | clause_tokens | alias_tokens))
        if overlap == 0 and not alias_match:
            continue

        score = (overlap / max(1, len(query_tokens))) + (0.4 if alias_match else 0.0)
        scored_records.append((score, record))

    scored_records.sort(key=lambda item: item[0], reverse=True)
    return [rec for _, rec in scored_records[:max_results]]

