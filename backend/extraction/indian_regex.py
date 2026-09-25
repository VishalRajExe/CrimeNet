"""
CrimeNet AI - Specialized Indian Law Enforcement Regex Patterns
Provides deterministic, zero-latency extraction of Indian investigative identifiers:
- Mobile Numbers (+91 / 10-digit)
- Vehicle Registration (RTO standard format)
- UPI Handles (VPA handles across all major Indian banks)
- Bank Account & IFSC Codes
- Indian Legal Acts (BNS, BNSS, CrPC, IPC, PMLA)
- Monetary Amounts (Lakhs, Crores, INR, ₹)
"""

import re
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class ExtractedToken:
    token_type: str  # 'PHONE', 'VEHICLE', 'UPI', 'IFSC', 'ACCOUNT', 'LEGAL_SECTION', 'AMOUNT'
    raw_value: str
    normalized_value: str
    start_pos: int
    end_pos: int
    metadata: Dict[str, Any]


class IndianRegexExtractor:
    """Deterministic extractor for Indian investigative entities."""

    # 1. Phone: Indian 10-digit mobile starting with 6, 7, 8, 9
    PHONE_REGEX = re.compile(
        r"(?:(?:\+91[\s.-]?)|(?:0[\s.-]?))?([6-9]\d{4}[\s.-]?\d{5})\b"
    )

    # 2. Vehicle: Standard Indian RTO format (e.g. MH04AB9901, DL 01 AB 1234, KA-05-M-4321)
    VEHICLE_REGEX = re.compile(
        r"\b([A-Z]{2}[\s.-]?[0-9]{1,2}[\s.-]?[A-Z]{1,3}[\s.-]?[0-9]{4})\b"
    )

    # 3. UPI VPAs: username@bank
    UPI_REGEX = re.compile(
        r"\b([a-zA-Z0-9._-]+@(okhdfcbank|okaxis|okicici|oksbi|paytm|ybl|ibl|upi|sbi|axis|icici|hdfc|kotak|postbank))\b",
        re.IGNORECASE
    )

    # 4. IFSC Code: 4 alphabetic chars, 0, 6 alphanumeric (e.g. SBIN0001234, HDFC0000409)
    IFSC_REGEX = re.compile(
        r"\b([A-Z]{4}0[A-Z0-9]{6})\b"
    )

    # 5. Bank Account Numbers: 9 to 18 digits preceded by account context
    ACCOUNT_REGEX = re.compile(
        r"(?:(?:A/C|A/c|Account|acct|acc|mule|sbi|hdfc|icici|axis)\s*(?:no\.?|num|number)?\s*[:#-]?\s*)([0-9]{9,18})\b",
        re.IGNORECASE
    )

    # 6. Legal Sections: CrPC, BNSS, BNS, IPC, PMLA
    LEGAL_REGEX = re.compile(
        r"\b(?:Section|Sec\.?)\s*([0-9]{1,3}(?:\([0-9a-zA-Z]+\))?)\s*(?:of\s+)?(CrPC|BNSS|BNS|IPC|PMLA|IT\s+Act|NDPS)\b",
        re.IGNORECASE
    )

    # 7. Monetary Amounts (Lakhs, Crores, INR, ₹)
    AMOUNT_REGEX = re.compile(
        r"(?:(?:Rs\.?|INR|₹)\s*([0-9,]+(?:\.[0-9]{1,2})?(?:\s*(?:Lakhs?|Crores?|Cr|L|k))?))|"
        r"([0-9]+(?:\.[0-9]{1,2})?\s*(?:Lakhs?|Crores?|Cr))\b",
        re.IGNORECASE
    )

    @classmethod
    def extract_all(cls, text: str) -> List[ExtractedToken]:
        tokens: List[ExtractedToken] = []

        # Extract Phones
        for match in cls.PHONE_REGEX.finditer(text):
            raw = match.group(0)
            digits = re.sub(r"\D", "", raw)
            if len(digits) >= 10:
                normalized = digits[-10:]  # Last 10 digits
                tokens.append(
                    ExtractedToken(
                        token_type="PHONE",
                        raw_value=raw,
                        normalized_value=normalized,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        metadata={"format": "Indian Mobile (+91)"}
                    )
                )

        # Extract Vehicles
        for match in cls.VEHICLE_REGEX.finditer(text):
            raw = match.group(0)
            cleaned = re.sub(r"[\s.-]", "", raw).upper()
            tokens.append(
                ExtractedToken(
                    token_type="VEHICLE",
                    raw_value=raw,
                    normalized_value=cleaned,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    metadata={"rto_state": cleaned[:2]}
                )
            )

        # Extract UPI handles
        for match in cls.UPI_REGEX.finditer(text):
            raw = match.group(0)
            norm = raw.strip().lower()
            tokens.append(
                ExtractedToken(
                    token_type="UPI_ACCOUNT",
                    raw_value=raw,
                    normalized_value=norm,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    metadata={"provider": norm.split("@")[-1]}
                )
            )

        # Extract IFSC codes
        for match in cls.IFSC_REGEX.finditer(text):
            raw = match.group(0)
            tokens.append(
                ExtractedToken(
                    token_type="IFSC",
                    raw_value=raw,
                    normalized_value=raw.upper(),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    metadata={"bank_code": raw[:4].upper()}
                )
            )

        # Extract Account Numbers
        for match in cls.ACCOUNT_REGEX.finditer(text):
            acc_num = match.group(1)
            tokens.append(
                ExtractedToken(
                    token_type="BANK_ACCOUNT",
                    raw_value=match.group(0),
                    normalized_value=acc_num,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    metadata={"digits": len(acc_num)}
                )
            )

        # Extract Legal Sections
        for match in cls.LEGAL_REGEX.finditer(text):
            section = match.group(1)
            act = match.group(2).upper()
            tokens.append(
                ExtractedToken(
                    token_type="LEGAL_SECTION",
                    raw_value=match.group(0),
                    normalized_value=f"{act} Section {section}",
                    start_pos=match.start(),
                    end_pos=match.end(),
                    metadata={"act": act, "section": section}
                )
            )

        # Extract Amounts
        for match in cls.AMOUNT_REGEX.finditer(text):
            val = match.group(1) or match.group(2)
            tokens.append(
                ExtractedToken(
                    token_type="AMOUNT",
                    raw_value=match.group(0),
                    normalized_value=f"₹{val.strip()}",
                    start_pos=match.start(),
                    end_pos=match.end(),
                    metadata={}
                )
            )

        return tokens
