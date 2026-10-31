"""Reviewed financial knowledge corpus with multi-collection structure and metadata.

Conforms to rag_docs.md specifications and .agents/skills/rag-implementation standards.
Supports three logical collections:
1. Regulatory Knowledge (RBI, IRDAI, NPCI)
2. Provider & Product Knowledge (lender norms, fee standards, KFS disclosure)
3. Assistant Policies (Sahayak operational boundaries, deterministic calculator rules)
"""

import hashlib
from typing import Any, Dict, List


def _compute_hash(content: str) -> str:
    return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()


KNOWLEDGE_SOURCES: List[Dict[str, Any]] = [
    # --------------------------------------------------------------------------
    # 1. ASSISTANT POLICIES (Operational & Ethical Boundaries)
    # --------------------------------------------------------------------------
    {
        "id": "sahayak_scope_v1",
        "collection_type": "assistant_policy",
        "source_name": "Sahayak Product Policy",
        "source_url": "https://sahayakai.in/policy/scope",
        "document_name": "Sahayak AI Product Policy",
        "document_type": "Policy",
        "financial_category": "assistant_boundary",
        "provider_name": "Sahayak AI",
        "version": "2026-10-v1",
        "owner": "Sahayak Product and Safety",
        "jurisdiction": "IN",
        "published_at": "2026-10-30",
        "effective_from": "2026-10-30",
        "effective_date": "2026-10-30",
        "review_due": "2027-10-30",
        "last_verified_at": "2026-10-31",
        "status": "active",
        "allowed_use": "assistant_grounding",
        "clause": "Assistant role and lender decisions",
        "approved": True,
        "text": (
            "Sahayak is a financial readiness and information assistant, not a lender. "
            "Only the relevant authorized lender makes loan approval, rejection, and disbursement decisions. "
            "Sahayak cannot guarantee an approval or predict an individual credit decision."
        ),
        "aliases": [
            "what is sahayak", "about sahayak", "sahayak kya hai", "sahayak kya karta hai",
            "loan approve", "loan approval", "pakka approve", "loan pass", "will i get loan",
            "loan milega", "kya mera loan", "credit decision", "lender approval",
            "guarantee my loan", "guarantee loan", "guarantee approval",
            "सहायक", "सहायक क्या है", "सहायक क्या करता है", "क्या मेरा लोन मिलेगा",
            "लोन मंजूर", "लोन अप्रूव", "ऋण स्वीकृति"
        ],
    },
    {
        "id": "sahayak_financial_values_v1",
        "collection_type": "assistant_policy",
        "source_name": "Sahayak Product Policy",
        "source_url": "https://sahayakai.in/policy/calculations",
        "document_name": "Sahayak AI Product Policy",
        "document_type": "Policy",
        "financial_category": "financial_calculations",
        "provider_name": "Sahayak AI",
        "version": "2026-10-v1",
        "owner": "Sahayak Product and Safety",
        "jurisdiction": "IN",
        "published_at": "2026-10-30",
        "effective_from": "2026-10-30",
        "effective_date": "2026-10-30",
        "review_due": "2027-10-30",
        "last_verified_at": "2026-10-31",
        "status": "active",
        "allowed_use": "assistant_grounding",
        "clause": "Financial calculations and offer values",
        "approved": True,
        "text": (
            "Loan amounts, EMI, interest, fees, taxes, APR, repayment schedules, and offer terms "
            "must come from the deterministic backend financial service and its current product data. "
            "The conversational assistant must not calculate, estimate, or invent these values."
        ),
        "aliases": [
            "emi", "interest rate", "apr", "processing fee", "gst", "monthly payment", "kisht",
            "exact emi", "calculate emi", "ईएमआई", "ब्याज दर", "किस्त", "प्रोसेसिंग फीस", "शुल्क"
        ],
    },
    {
        "id": "sahayak_kfs_foreclosure_v1",
        "collection_type": "assistant_policy",
        "source_name": "Sahayak Product Policy",
        "source_url": "https://sahayakai.in/policy/kfs-foreclosure",
        "document_name": "Sahayak AI Product Policy",
        "document_type": "Policy",
        "financial_category": "product_terms",
        "provider_name": "Sahayak AI",
        "version": "2026-10-v1",
        "owner": "Sahayak Product and Safety",
        "jurisdiction": "IN",
        "published_at": "2026-10-30",
        "effective_from": "2026-10-30",
        "effective_date": "2026-10-30",
        "review_due": "2027-10-30",
        "last_verified_at": "2026-10-31",
        "status": "active",
        "allowed_use": "assistant_grounding",
        "clause": "Lender documents and product-specific terms",
        "approved": True,
        "text": (
            "A Key Fact Statement (KFS) and lender-specific terms, including foreclosure terms, "
            "must be read from the current lender-issued documents. Sahayak does not maintain "
            "approved lender-specific KFS or foreclosure terms in this assistant corpus."
        ),
        "aliases": [
            "key fact statement", "kfs", "foreclosure", "prepayment charges", "lender document",
            "lender terms", "lender kfs", "मुख्य तथ्य विवरण", "फोरक्लोज़र", "पूर्व भुगतान शुल्क"
        ],
    },
    {
        "id": "sahayak_document_review_v1",
        "collection_type": "assistant_policy",
        "source_name": "Sahayak Product Policy",
        "source_url": "https://sahayakai.in/policy/document-privacy",
        "document_name": "Sahayak AI Product Policy",
        "document_type": "Policy",
        "financial_category": "privacy_and_documents",
        "provider_name": "Sahayak AI",
        "version": "2026-10-v1",
        "owner": "Sahayak Product and Safety",
        "jurisdiction": "IN",
        "published_at": "2026-10-30",
        "effective_from": "2026-10-30",
        "effective_date": "2026-10-30",
        "review_due": "2027-10-30",
        "last_verified_at": "2026-10-31",
        "status": "active",
        "allowed_use": "assistant_grounding",
        "clause": "Document extraction and customer confirmation",
        "approved": True,
        "text": (
            "Document extraction is handled by a separate OCR and preflight workflow. "
            "Raw documents and OCR text are not sent to the conversational model. "
            "Extracted fields remain unverified until the customer reviews and confirms them."
        ),
        "aliases": [
            "document", "ocr", "pan", "aadhaar", "bank statement", "salary slip", "extract",
            "uploaded pan", "read my document", "दस्तावेज़", "पैन", "आधार", "बैंक स्टेटमेंट", "सैलरी स्लिप"
        ],
    },

    # --------------------------------------------------------------------------
    # 2. REGULATORY KNOWLEDGE (RBI, IRDAI, NPCI)
    # --------------------------------------------------------------------------
    {
        "id": "rbi_digital_lending_kfs_v1",
        "collection_type": "regulatory",
        "source_name": "Reserve Bank of India",
        "source_url": "https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12554",
        "document_name": "RBI Guidelines on Digital Lending",
        "document_type": "Master Direction",
        "financial_category": "digital_lending",
        "provider_name": "RBI",
        "version": "2022-09-v1",
        "owner": "RBI Financial Regulation Department",
        "jurisdiction": "IN",
        "published_at": "2022-09-02",
        "effective_from": "2022-09-02",
        "effective_date": "2022-09-02",
        "review_due": "2027-12-31",
        "last_verified_at": "2026-10-31",
        "status": "active",
        "allowed_use": "assistant_grounding",
        "clause": "Mandatory Key Fact Statement (KFS) and Fee Disclosure",
        "approved": True,
        "text": (
            "Under RBI Digital Lending Directions, regulated lenders must provide a standardized Key Fact Statement (KFS) "
            "to the borrower before loan agreement execution. The KFS must clearly disclose the all-inclusive Annual Percentage Rate (APR), "
            "detailed fee breakdown, recovery terms, and cooling-off period. Lenders cannot levy any fee or charge not explicitly disclosed in the KFS."
        ),
        "aliases": [
            "key fact statement", "kfs", "apr", "annual percentage rate", "hidden charges",
            "digital lending directions", "rbi digital lending", "rbi rules", "kfs rule",
            "hidden fees", "kfs kya hai", "kfs kyu zaroori hai", "rbi loan rules",
            "rules regarding key fact statement", "kfs and hidden charges",
            "मुख्य तथ्य विवरण", "आरबीआई डिजिटल लेंडिंग", "केएफएस", "छिपे हुए शुल्क", "वार्षिक प्रतिशत दर"
        ],
    },
    {
        "id": "rbi_digital_lending_cooling_off_v1",
        "collection_type": "regulatory",
        "source_name": "Reserve Bank of India",
        "source_url": "https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12554",
        "document_name": "RBI Guidelines on Digital Lending",
        "document_type": "Master Direction",
        "financial_category": "borrower_rights",
        "provider_name": "RBI",
        "version": "2022-09-v1",
        "owner": "RBI Financial Regulation Department",
        "jurisdiction": "IN",
        "published_at": "2022-09-02",
        "effective_from": "2022-09-02",
        "effective_date": "2022-09-02",
        "review_due": "2027-12-31",
        "last_verified_at": "2026-10-31",
        "status": "active",
        "allowed_use": "assistant_grounding",
        "clause": "Mandatory Cooling-off and Look-up Period",
        "approved": True,
        "text": (
            "Under RBI Digital Lending Directions, borrowers have a mandatory cooling-off or look-up period to exit a digital loan "
            "without paying any penalty. The cooling-off period is at least 3 days for loans having a tenure of 7 days or more, "
            "and 1 day for loans with a tenure under 7 days. The borrower exits by paying only the principal and proportionate APR."
        ),
        "aliases": [
            "cooling off period", "look up period", "cancel digital loan", "exit loan without penalty",
            "loan cancellation", "rbi cooling off", "cooling off", "cooling off kya hai",
            "loan cancel kaise kare", "look-up period", "exit loan penalty",
            "कूलिंग ऑफ अवधि", "लोन रद्द करना", "बिना पेनल्टी लोन रद्द"
        ],
    },
    {
        "id": "rbi_disbursement_direct_account_v1",
        "collection_type": "regulatory",
        "source_name": "Reserve Bank of India",
        "source_url": "https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12554",
        "document_name": "RBI Guidelines on Digital Lending",
        "document_type": "Master Direction",
        "financial_category": "disbursement_rules",
        "provider_name": "RBI",
        "version": "2022-09-v1",
        "owner": "RBI Financial Regulation Department",
        "jurisdiction": "IN",
        "published_at": "2022-09-02",
        "effective_from": "2022-09-02",
        "effective_date": "2022-09-02",
        "review_due": "2027-12-31",
        "last_verified_at": "2026-10-31",
        "status": "active",
        "allowed_use": "assistant_grounding",
        "clause": "Direct Loan Disbursal and Repayment Flow",
        "approved": True,
        "text": (
            "Under RBI guidelines, all loan disbursements and repayments must execute directly between the bank account "
            "of the Regulated Entity (the bank or NBFC) and the borrower. Disbursals cannot flow through pool accounts "
            "or pass-through accounts of third-party Lending Service Providers (LSPs) or digital apps."
        ),
        "aliases": [
            "direct disbursement", "pool account", "lsp account", "third party account",
            "rbi disbursement", "paisa kiske account me aayega", "pass through account",
            "लोन वितरण", "सीधे बैंक खाते में ट्रांसफर"
        ],
    },
    {
        "id": "rbi_recovery_agents_conduct_v1",
        "collection_type": "regulatory",
        "source_name": "Reserve Bank of India",
        "source_url": "https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12554",
        "document_name": "RBI Fair Practices Code & Digital Lending Directions",
        "document_type": "Master Direction",
        "financial_category": "recovery_conduct",
        "provider_name": "RBI",
        "version": "2022-09-v1",
        "owner": "RBI Department of Consumer Education and Protection",
        "jurisdiction": "IN",
        "published_at": "2022-09-02",
        "effective_from": "2022-09-02",
        "effective_date": "2022-09-02",
        "review_due": "2027-12-31",
        "last_verified_at": "2026-10-31",
        "status": "active",
        "allowed_use": "assistant_grounding",
        "clause": "Recovery Agent Calling Hours and Harassment Prohibitions",
        "approved": True,
        "text": (
            "Under RBI Fair Practices Code and Digital Lending Directions, recovery agents are strictly prohibited from contacting "
            "borrowers before 08:00 AM or after 07:00 PM. Lenders and their agents cannot harass, intimidate, use abusive language, "
            "publicly humiliate borrowers, or contact friends and relatives from phone contact lists."
        ),
        "aliases": [
            "recovery agent", "recovery call time", "recovery agent calling hours", "recovery agent harassment",
            "can recovery agent call at night", "harassment by recovery agent", "recovery rules",
            "recovery agent raat me call", "recovery agent dhamki", "calling hours 8am 7pm", "calling hours",
            "रिकवरी एजेंट", "रिकवरी एजेंट कॉल का समय", "रिकवरी एजेंट धमकी", "रिकवरी एजेंट रात में"
        ],
    },
    {
        "id": "rbi_foreclosure_charges_floating_v1",
        "collection_type": "regulatory",
        "source_name": "Reserve Bank of India",
        "source_url": "https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=8925",
        "document_name": "RBI Master Directions on Prepayment and Foreclosure",
        "document_type": "Circular",
        "financial_category": "foreclosure_norms",
        "provider_name": "RBI",
        "version": "2014-05-v1",
        "owner": "RBI Financial Regulation Department",
        "jurisdiction": "IN",
        "published_at": "2014-05-07",
        "effective_from": "2014-05-07",
        "effective_date": "2014-05-07",
        "review_due": "2027-12-31",
        "last_verified_at": "2026-10-31",
        "status": "active",
        "allowed_use": "assistant_grounding",
        "clause": "Prohibition of Foreclosure Charges on Floating-Rate Personal Loans",
        "approved": True,
        "text": (
            "Under RBI regulations, banks and NBFCs are strictly prohibited from levying any foreclosure charges or prepayment penalties "
            "on floating-rate term loans sanctioned to individual borrowers for purposes other than business. Fixed-rate personal loans "
            "may levy prepayment charges only as specified in the agreed Key Fact Statement."
        ),
        "aliases": [
            "foreclosure charges", "prepayment penalty", "prepayment charges", "floating rate foreclosure",
            "preclose loan", "loan band karne ka charge", "rbi foreclosure rule", "floating personal loans",
            "foreclosure charges on floating loans", "prepayment charges floating personal loans",
            "फोरक्लोज़र शुल्क", "प्रीपेमेंट पेनल्टी", "लोन बंद करने का शुल्क"
        ],
    },
    {
        "id": "rbi_grievance_cms_portal_v1",
        "collection_type": "regulatory",
        "source_name": "Reserve Bank of India",
        "source_url": "https://cms.rbi.org.in",
        "document_name": "RBI Integrated Ombudsman Scheme",
        "document_type": "Directions",
        "financial_category": "grievance_redressal",
        "provider_name": "RBI",
        "version": "2021-11-v1",
        "owner": "RBI Consumer Education and Protection Department",
        "jurisdiction": "IN",
        "published_at": "2021-11-12",
        "effective_from": "2021-11-12",
        "effective_date": "2021-11-12",
        "review_due": "2027-12-31",
        "last_verified_at": "2026-10-31",
        "status": "active",
        "allowed_use": "assistant_grounding",
        "clause": "Grievance Redressal and RBI CMS Portal Escalation",
        "approved": True,
        "text": (
            "Every regulated lender and digital lending partner must appoint a dedicated Nodal Grievance Redressal Officer. "
            "If a customer complaint is not resolved within 30 days, or if the borrower is dissatisfied with the response, "
            "the borrower can lodge a complaint with the RBI Banking Ombudsman via the RBI Complaint Management System (CMS) at cms.rbi.org.in."
        ),
        "aliases": [
            "grievance redressal", "rbi cms", "banking ombudsman", "complaint against lender",
            "rbi complaint portal", "shikayat kaise kare", "lokpal", "cms portal", "30 days complaint",
            "शिकायत निवारण", "आरबीआई सीएमएस", "बैंकिंग लोकपाल"
        ],
    },
    {
        "id": "rbi_sachet_portal_v1",
        "collection_type": "regulatory",
        "source_name": "Reserve Bank of India - Sachet",
        "source_url": "https://sachet.rbi.org.in",
        "document_name": "RBI Sachet Consumer Awareness Initiative",
        "document_type": "Portal Resource",
        "financial_category": "consumer_awareness",
        "provider_name": "RBI Sachet",
        "version": "2020-01-v1",
        "owner": "State Level Coordination Committee (SLCC)",
        "jurisdiction": "IN",
        "published_at": "2020-01-01",
        "effective_from": "2020-01-01",
        "effective_date": "2020-01-01",
        "review_due": "2027-12-31",
        "last_verified_at": "2026-10-31",
        "status": "active",
        "allowed_use": "assistant_grounding",
        "clause": "RBI Sachet Portal for Unauthorized Lending Apps",
        "approved": True,
        "text": (
            "The RBI Sachet portal (sachet.rbi.org.in) allows citizens to verify registered financial entities and report "
            "unauthorized lending apps, fraudulent investment schemes, and unregistered deposit companies. Users should verify "
            "that a lending app is partnered with a registered Bank or NBFC before sharing sensitive information."
        ),
        "aliases": [
            "sachet", "rbi sachet", "fake loan app", "fraud lending app", "unauthorized app",
            "sachet portal", "check registered nbfc", "verify loan app", "फर्जी लोन ऐप", "सचेत पोर्टल"
        ],
    },
    {
        "id": "irdai_insurance_freelook_v1",
        "collection_type": "regulatory",
        "source_name": "Insurance Regulatory and Development Authority of India",
        "source_url": "https://irdai.gov.in",
        "document_name": "IRDAI Policyholder Protection Regulations",
        "document_type": "Regulation",
        "financial_category": "insurance_rights",
        "provider_name": "IRDAI",
        "version": "2017-04-v1",
        "owner": "IRDAI Policyholder Protection Department",
        "jurisdiction": "IN",
        "published_at": "2017-04-01",
        "effective_from": "2017-04-01",
        "effective_date": "2017-04-01",
        "review_due": "2027-12-31",
        "last_verified_at": "2026-10-31",
        "status": "active",
        "allowed_use": "assistant_grounding",
        "clause": "IRDAI Insurance Free-Look Period and Cancellation Rights",
        "approved": True,
        "text": (
            "Under IRDAI regulations, every life and health insurance policyholder has a free-look period of 15 days "
            "(30 days for policies purchased electronically or via distance marketing) from policy receipt to review terms. "
            "If the policyholder disagrees with any clause, they can cancel the policy and receive a full refund of premium, "
            "less proportionate risk premium and medical test expenses."
        ),
        "aliases": [
            "free look period", "insurance free look", "cancel insurance policy", "irdai free look",
            "policy cancellation", "insurance refund", "insurance exclusions", "free look 15 days",
            "free look 30 days", "फ्री लुक पीरियड", "बीमा पॉलिसी रद्द", "बीमा रिफंड"
        ],
    },
    {
        "id": "npci_upi_dispute_turnaround_v1",
        "collection_type": "regulatory",
        "source_name": "National Payments Corporation of India",
        "source_url": "https://www.npci.org.in",
        "document_name": "NPCI UPI Operating Guidelines and Harmonization",
        "document_type": "Circular & FAQ",
        "financial_category": "upi_payments",
        "provider_name": "NPCI",
        "version": "2020-08-v1",
        "owner": "NPCI Product & Dispute Management",
        "jurisdiction": "IN",
        "published_at": "2020-08-01",
        "effective_from": "2020-08-01",
        "effective_date": "2020-08-01",
        "review_due": "2027-12-31",
        "last_verified_at": "2026-10-31",
        "status": "active",
        "allowed_use": "assistant_grounding",
        "clause": "UPI Transaction Dispute and Auto-Reversal Turnaround",
        "approved": True,
        "text": (
            "Under NPCI and RBI harmonization guidelines, when a UPI transaction fails where money is debited from the payer's account "
            "but not credited to the beneficiary, auto-reversal must complete within T+1 business days. If the bank fails to reverse within "
            "this turnaround time, the bank must pay compensation of 100 rupees per day of delay to the customer."
        ),
        "aliases": [
            "upi failed transaction", "upi refund", "auto reversal", "t+1 reversal", "upi dispute",
            "upi transaction fail", "paisa kat gaya", "upi compensation 100", "upi issue",
            "यूपीआई फेल", "यूपीआई रिफंड", "पैसे कट गए"
        ],
    },
    {
        "id": "rbi_customer_liability_unauthorized_v1",
        "collection_type": "regulatory",
        "source_name": "Reserve Bank of India",
        "source_url": "https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=11040",
        "document_name": "RBI Customer Protection - Limiting Liability in Electronic Banking",
        "document_type": "Circular",
        "financial_category": "fraud_liability",
        "provider_name": "RBI",
        "version": "2017-07-v1",
        "owner": "RBI Department of Banking Regulation",
        "jurisdiction": "IN",
        "published_at": "2017-07-06",
        "effective_from": "2017-07-06",
        "effective_date": "2017-07-06",
        "review_due": "2027-12-31",
        "last_verified_at": "2026-10-31",
        "status": "active",
        "allowed_use": "assistant_grounding",
        "clause": "Zero Customer Liability for Unauthorized Electronic Transactions",
        "approved": True,
        "text": (
            "Under RBI customer protection directions, a customer has zero liability for unauthorized electronic banking and payment "
            "transactions if the unauthorized transaction occurs due to contributory fraud/negligence by the bank, or if third-party "
            "breach occurs and the customer notifies the bank within 3 working days of receiving the alert."
        ),
        "aliases": [
            "unauthorized transaction", "zero liability", "fraud transaction", "bank fraud liability",
            "fraud alert 3 days", "3 working days fraud", "anadhikrit len den", "fraud report",
            "धोखाधड़ी लेनदेन", "शून्य देनदारी", "बैंक फ्रॉड"
        ],
    },

    # --------------------------------------------------------------------------
    # 3. PROVIDER & PRODUCT NORMS (Market Terms, Fees, KFS Guidelines)
    # --------------------------------------------------------------------------
    {
        "id": "provider_fee_and_gst_norms_v1",
        "collection_type": "provider",
        "source_name": "Banking & NBFC Industry Standards",
        "source_url": "https://sahayakai.in/policy/provider-standards",
        "document_name": "Indian Retail Lending Market Norms",
        "document_type": "Standard Guideline",
        "financial_category": "loan_pricing",
        "provider_name": "Authorized Lenders",
        "version": "2026-10-v1",
        "owner": "Market Research Group",
        "jurisdiction": "IN",
        "published_at": "2026-10-01",
        "effective_from": "2026-10-01",
        "effective_date": "2026-10-01",
        "review_due": "2027-10-30",
        "last_verified_at": "2026-10-31",
        "status": "active",
        "allowed_use": "assistant_grounding",
        "clause": "Loan Processing Fees and 18% GST Application",
        "approved": True,
        "text": (
            "Authorized lenders typically charge a processing fee ranging from 1.0% to 3.0% of the sanctioned loan amount. "
            "All processing fees and loan charges in India attract 18% Goods and Services Tax (GST). All fees and applicable "
            "taxes must be explicitly listed in the Key Fact Statement before disbursal."
        ),
        "aliases": [
            "processing fee", "gst on loan", "processing fee gst", "loan charges", "18% gst",
            "processing fee kitni lagti hai", "standard processing fee", "gst charges",
            "प्रोसेसिंग फीस", "जीएसटी"
        ],
    },
    {
        "id": "provider_fixed_vs_floating_terms_v1",
        "collection_type": "provider",
        "source_name": "Banking & NBFC Industry Standards",
        "source_url": "https://sahayakai.in/policy/provider-standards",
        "document_name": "Indian Retail Lending Market Norms",
        "document_type": "Standard Guideline",
        "financial_category": "product_terms",
        "provider_name": "Authorized Lenders",
        "version": "2026-10-v1",
        "owner": "Market Research Group",
        "jurisdiction": "IN",
        "published_at": "2026-10-01",
        "effective_from": "2026-10-01",
        "effective_date": "2026-10-01",
        "review_due": "2027-10-30",
        "last_verified_at": "2026-10-31",
        "status": "active",
        "allowed_use": "assistant_grounding",
        "clause": "Fixed versus Floating Interest Rate Prepayment Differences",
        "approved": True,
        "text": (
            "In consumer lending, floating interest rates adjust with benchmark rates (such as RBI repo rate) and carry zero "
            "prepayment penalty by RBI mandate. Fixed interest rates remain constant throughout the tenure and may include "
            "contractual prepayment charges as specified in the lender's individual loan agreement."
        ),
        "aliases": [
            "fixed vs floating", "floating interest rate", "fixed interest rate", "prepayment differences",
            "difference between fixed and floating", "फ्लोटिंग बनाम फिक्स्ड", "फिक्स्ड ब्याज दर"
        ],
    },
]

# Compute SHA-256 content hashes for all items
for _source in KNOWLEDGE_SOURCES:
    if "content_hash" not in _source:
        _source["content_hash"] = _compute_hash(_source["text"])
