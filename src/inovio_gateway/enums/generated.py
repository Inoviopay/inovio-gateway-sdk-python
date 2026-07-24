"""GENERATED FILE — DO NOT EDIT.

Source: Inovio Gateway Payments Service API v4.14 (api-sdk/spec/spec-enums.json)
Regenerate: python scripts/generate_enums.py

Classifiers (retryable/terminal/stopRecurring, AVS/CVV classification and the
API-code -> exception mapping) are DERIVED by the SDK project, not stated in
the spec. See api-sdk/spec/README.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict


SPEC_API_VERSION = "4.14"


class TransactionStatus(str, Enum):
    """Appendix B — the master transaction lifecycle (5 states)."""
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    FAILED = "FAILED"


TRANSACTION_STATUS_DESCRIPTIONS: Dict[TransactionStatus, str] = {
    TransactionStatus.APPROVED: "Transaction has been approved.",
    TransactionStatus.DECLINED: "Transaction has been declined.",
    TransactionStatus.PENDING: "Transaction is in pending status (expected on 3-D Secure, and preauthorization of online check transactions (i.e. Boleto, ACH, Pix etc.)).",
    TransactionStatus.RUNNING: "Transaction processing is not completed or is waiting completion.",
    TransactionStatus.FAILED: "Transaction did not finish payment completion (used in European Direct Debit transactions)",
}


class RequestAction(str, Enum):
    """Appendix A — every REQUEST_ACTION the gateway accepts."""
    ACHAUTHCAP = "ACHAUTHCAP"
    ACHAUTHORIZE = "ACHAUTHORIZE"
    ACHREVERSE = "ACHREVERSE"
    ACHCREDIT = "ACHCREDIT"
    APPLEPAYCONFIG = "APPLEPAYCONFIG"
    CCAUTHORIZE = "CCAUTHORIZE"
    CCCAPTURE = "CCCAPTURE"
    CCAUTHCAP = "CCAUTHCAP"
    CCREVERSE = "CCREVERSE"
    CCREVERSECAP = "CCREVERSECAP"
    CCCREDIT = "CCCREDIT"
    CCRDR = "CCRDR"
    CCRDRDELETE = "CCRDRDELETE"
    CCTC40 = "CCTC40"
    CCSTATUS = "CCSTATUS"
    CCTRANSUPDATE = "CCTRANSUPDATE"
    DBTAUTHORIZE = "DBTAUTHORIZE"
    DBTCAPTURE = "DBTCAPTURE"
    DBTCREDIT = "DBTCREDIT"
    DBTDEBIT = "DBTDEBIT"
    DBTREVERSE = "DBTREVERSE"
    GOOGLEPAYCONFIG = "GOOGLEPAYCONFIG"
    TESTGW = "TESTGW"
    TESTAUTH = "TESTAUTH"
    SUB_CANCEL = "SUB_CANCEL"
    SUB_UPDATE = "SUB_UPDATE"
    BOLETOAUTHCAP = "BOLETOAUTHCAP"
    PIXSALE = "PIXSALE"
    PAGSALE = "PAGSALE"


@dataclass(frozen=True)
class ServiceResponseCodeInfo:
    code: int
    description: str
    retryable: bool
    stop_recurring: bool
    approval: bool
    terminal: bool


SERVICE_RESPONSE_CODES: Dict[int, ServiceResponseCodeInfo] = {
    100: ServiceResponseCodeInfo(100, "User Authorized", False, False, True, False),
    101: ServiceResponseCodeInfo(101, "Service Available", False, False, True, False),
    102: ServiceResponseCodeInfo(102, "Membership Updated", False, False, True, False),
    150: ServiceResponseCodeInfo(150, "Product Not Found", False, False, False, True),
    152: ServiceResponseCodeInfo(152, "Product Type Not Found", False, False, False, True),
    155: ServiceResponseCodeInfo(155, "Selected currency not configured", False, False, False, True),
    157: ServiceResponseCodeInfo(157, "MID has RDR Status OFF", False, False, False, True),
    190: ServiceResponseCodeInfo(190, "Invalid Product Configuration", False, False, False, True),
    192: ServiceResponseCodeInfo(192, "Product Not Active", False, False, False, True),
    200: ServiceResponseCodeInfo(200, "CVV required by processor", False, False, False, True),
    201: ServiceResponseCodeInfo(201, "Country required by processor", False, False, False, True),
    202: ServiceResponseCodeInfo(202, "DOB required by processor", False, False, False, True),
    203: ServiceResponseCodeInfo(203, "SSN required by processor", False, False, False, True),
    204: ServiceResponseCodeInfo(204, "Address required by processor", False, False, False, True),
    205: ServiceResponseCodeInfo(205, "City required by processor", False, False, False, True),
    206: ServiceResponseCodeInfo(206, "State required by processor", False, False, False, True),
    207: ServiceResponseCodeInfo(207, "Postal Code required by processor", False, False, False, True),
    208: ServiceResponseCodeInfo(208, "Phone required by processor", False, False, False, True),
    209: ServiceResponseCodeInfo(209, "IP required by processor", False, False, False, True),
    210: ServiceResponseCodeInfo(210, "CPF required by processor", False, False, False, True),
    211: ServiceResponseCodeInfo(211, "Email required by processor", False, False, False, True),
    212: ServiceResponseCodeInfo(212, "FName required by processor", False, False, False, True),
    213: ServiceResponseCodeInfo(213, "LName required by processor", False, False, False, True),
    215: ServiceResponseCodeInfo(215, "Activity limit exceeded", False, False, False, True),
    216: ServiceResponseCodeInfo(216, "Invalid amount", False, False, False, True),
    217: ServiceResponseCodeInfo(217, "No such issuer", False, False, False, True),
    218: ServiceResponseCodeInfo(218, "Wrong PIN entered", False, False, False, True),
    219: ServiceResponseCodeInfo(219, "R0: Stop recurring payments", False, True, False, True),
    220: ServiceResponseCodeInfo(220, "R1: Stop recurring payments", False, True, False, True),
    221: ServiceResponseCodeInfo(221, "System malfunction", False, False, False, True),
    500: ServiceResponseCodeInfo(500, "No merchant account configured", False, False, False, True),
    501: ServiceResponseCodeInfo(501, "Customer not found", False, False, False, True),
    502: ServiceResponseCodeInfo(502, "Transaction error", False, False, False, True),
    503: ServiceResponseCodeInfo(503, "Service Unavailable", False, False, False, True),
    505: ServiceResponseCodeInfo(505, "Order adjusted to zero", False, False, False, True),
    506: ServiceResponseCodeInfo(506, "Capture amount exceeds order value", False, False, False, True),
    507: ServiceResponseCodeInfo(507, "Order fully captured", False, False, False, True),
    510: ServiceResponseCodeInfo(510, "Order already reversed", False, False, False, True),
    511: ServiceResponseCodeInfo(511, "Order already charged back", False, False, False, True),
    512: ServiceResponseCodeInfo(512, "Order not found", False, False, False, True),
    515: ServiceResponseCodeInfo(515, "Order fully credited", False, False, False, True),
    516: ServiceResponseCodeInfo(516, "Credit amount exceeds order value", False, False, False, True),
    518: ServiceResponseCodeInfo(518, "Missing required field", False, False, False, True),
    520: ServiceResponseCodeInfo(520, "Unsupported Currency", False, False, False, True),
    522: ServiceResponseCodeInfo(522, "Unsupported card brand", False, False, False, True),
    525: ServiceResponseCodeInfo(525, "Batch Closed: Please credit", False, False, False, True),
    526: ServiceResponseCodeInfo(526, "ApplePay is not supported on this merch_acct_id", False, False, False, True),
    527: ServiceResponseCodeInfo(527, "No ApplePay merch_acct_id configured", False, False, False, True),
    528: ServiceResponseCodeInfo(528, "ApplePay MCC Restricted", False, False, False, True),
    530: ServiceResponseCodeInfo(530, "Downstream Processor Unavailable", False, False, False, True),
    536: ServiceResponseCodeInfo(536, "Order not settled: Please reverse", False, False, False, True),
    540: ServiceResponseCodeInfo(540, "Maximum Auth Limit Exceeded", False, False, False, True),
    546: ServiceResponseCodeInfo(546, "GooglePay MCC Restricted", False, False, False, True),
    547: ServiceResponseCodeInfo(547, "No GooglePay merch_acct_id configured", False, False, False, True),
    548: ServiceResponseCodeInfo(548, "GooglePay is not supported on this merch_acct_id", False, False, False, True),
    555: ServiceResponseCodeInfo(555, "Call Center", False, False, False, True),
    560: ServiceResponseCodeInfo(560, "Invalid Service Action", False, False, False, True),
    564: ServiceResponseCodeInfo(564, "Invalid Terminal", False, False, False, True),
    565: ServiceResponseCodeInfo(565, "Invalid Amount", False, False, False, True),
    570: ServiceResponseCodeInfo(570, "Invalid Card Type", False, False, False, True),
    580: ServiceResponseCodeInfo(580, "Unsupported Request", False, False, False, True),
    600: ServiceResponseCodeInfo(600, "Declined", False, False, False, True),
    601: ServiceResponseCodeInfo(601, "Scrub Decline", False, False, False, True),
    603: ServiceResponseCodeInfo(603, "Fraud", False, False, False, True),
    605: ServiceResponseCodeInfo(605, "Stolen Card", False, False, False, True),
    610: ServiceResponseCodeInfo(610, "Pickup Card", False, False, False, True),
    615: ServiceResponseCodeInfo(615, "Lost Card", False, False, False, True),
    620: ServiceResponseCodeInfo(620, "Invalid CVV", False, False, False, True),
    621: ServiceResponseCodeInfo(621, "Failed CVV", False, False, False, True),
    622: ServiceResponseCodeInfo(622, "Invalid AVS", False, False, False, True),
    623: ServiceResponseCodeInfo(623, "Failed AVS", False, False, False, True),
    624: ServiceResponseCodeInfo(624, "Expired Card", False, False, False, True),
    625: ServiceResponseCodeInfo(625, "Excessive Use", False, False, False, True),
    630: ServiceResponseCodeInfo(630, "Invalid Card Number", False, False, False, True),
    635: ServiceResponseCodeInfo(635, "Insufficient Funds", True, False, False, False),
    640: ServiceResponseCodeInfo(640, "Retry", True, False, False, False),
    650: ServiceResponseCodeInfo(650, "Do Not Honor", False, False, False, True),
    660: ServiceResponseCodeInfo(660, "Partial Approval", True, False, False, False),
    670: ServiceResponseCodeInfo(670, "Additional Authentication Required", False, False, False, True),
    675: ServiceResponseCodeInfo(675, "Invalid Card Number, failed Mod 10 validation", False, False, False, True),
    680: ServiceResponseCodeInfo(680, "Duplicate Transaction Detected", False, False, False, True),
    685: ServiceResponseCodeInfo(685, "Duplicate Order Detected", False, False, False, True),
    690: ServiceResponseCodeInfo(690, "Active Membership Exists", False, False, False, True),
    692: ServiceResponseCodeInfo(692, "Invalid Rebill Product", False, False, False, True),
    695: ServiceResponseCodeInfo(695, "Site Username Unavailable", False, False, False, True),
    697: ServiceResponseCodeInfo(697, "Membership Not Active", False, False, False, True),
    698: ServiceResponseCodeInfo(698, "Membership Not Found", False, False, False, True),
    699: ServiceResponseCodeInfo(699, "Membership Not Set for Rebill", False, False, False, True),
    700: ServiceResponseCodeInfo(700, "Scrub Decline", False, False, False, True),
    706: ServiceResponseCodeInfo(706, "Failed Age Validation", False, False, False, True),
    707: ServiceResponseCodeInfo(707, "Invalid CPF", False, False, False, True),
}


@dataclass(frozen=True)
class ApiResponseCodeInfo:
    code: int
    description: str
    recommendation: str
    maps_to_exception: str
    carries_ref_field: bool


API_RESPONSE_CODES: Dict[int, ApiResponseCodeInfo] = {
    100: ApiResponseCodeInfo(100, "Invalid login information (throttle)", "Check your login credentials and try again. If you continue to receive this response, contact Client Support", "RateLimitException", False),
    101: ApiResponseCodeInfo(101, "Invalid login information", "Check your login credentials and try again. If you continue to receive this response, contact Client Support", "AuthenticationException", False),
    102: ApiResponseCodeInfo(102, "User not active", "These credentials have been disabled. If you think this is an error, contact Client Support", "AuthenticationException", False),
    103: ApiResponseCodeInfo(103, "Invalid site", "The value of SITE_ID does not exist, or it does not match the authentication credentials provided.", "AuthenticationException", False),
    104: ApiResponseCodeInfo(104, "Invalid service", "Check the value of request_action to confirm it is correct.", "AuthenticationException", False),
    105: ApiResponseCodeInfo(105, "Invalid service action", "Check the value of request_action to confirm it is correct.", "AuthenticationException", False),
    106: ApiResponseCodeInfo(106, "Invalid service object", "Check the value of request_object to confirm it is correct.", "AuthenticationException", False),
    110: ApiResponseCodeInfo(110, "Required field", "A required key/value pair has not been included in the request. In the response, check the value of REF_FIELD to see what is missing", "ValidationException", True),
    111: ApiResponseCodeInfo(111, "Invalid length", "The length of a value is too short or long. Check the returned value of REF_FIELD to see which field may need editing", "ValidationException", True),
    112: ApiResponseCodeInfo(112, "Not numeric", "Numeric data is expected. Confirm the amount sent for LI_VALUE_x, which should only contain numerals and one decimal Something in the request was not", "ValidationException", False),
    113: ApiResponseCodeInfo(113, "Invalid Data", "expected. Check the values that were submitted for unusual characters, spaces, or null values where there perhaps should not be", "ValidationException", False),
    115: ApiResponseCodeInfo(115, "Customer not found", "If CUST_ID or CUST_ID_XTL was submitted, check these values and try again. If this response has come from a request without these parameters, contact Client Support", "ValidationException", False),
    116: ApiResponseCodeInfo(116, "User MUST change password", "User passwords expire every 90 days. This does not apply to API credentials.", "ValidationException", False),
    118: ApiResponseCodeInfo(118, "New password must not match the previous 5 passwords", "Try a different password.", "ValidationException", False),
    119: ApiResponseCodeInfo(119, "request_ref_po_id and request_po_li_id mismatch", "The order ID and the line item ID do not relate to one another. Check the order information.", "ValidationException", False),
    120: ApiResponseCodeInfo(120, "System Error", "Contact Client Support", "ValidationException", False),
    125: ApiResponseCodeInfo(125, "Duplicate Login", "This email address, a unique identifier, already exists.", "ConfigurationException", False),
    130: ApiResponseCodeInfo(130, "Same Product ID found on different line items.", "Check the values of LI_PROD_ID_x. Each one should have a unique ID. If the intent is to submit a purchase for multiples of the same product use LI_COUNT_x to indicate the quantity.", "ConfigurationException", False),
    135: ApiResponseCodeInfo(135, "Duplicate Company Name", "This company name is already in the system. If you are certain it doesn't already exist in the system, it could be a company with the same name, but doing business in a different region. Contact Client Support for assistance.", "ConfigurationException", False),
    136: ApiResponseCodeInfo(136, "Duplicate Site Name", "This site name already exists in our system.", "ConfigurationException", False),
    150: ApiResponseCodeInfo(150, "Product Not Found", "The product ID is not valid. It may not exist, or it might be associated with another site. Check", "ConfigurationException", False),
    152: ApiResponseCodeInfo(152, "Product Type Not Found", "The value for PROD_TYPE is not valid.", "ConfigurationException", False),
    153: ApiResponseCodeInfo(153, "Duplicate XTL product id", "This value is already in the system. To confirm and review, the ID can be searched for in our", "ConfigurationException", False),
    155: ApiResponseCodeInfo(155, "Selected currency not configured", "Check the merchant account configuration in the portal.", "ConfigurationException", False),
    160: ApiResponseCodeInfo(160, "Invalid product amount", "Check the value of LI_VALUE_x to confirm it is the intended amount.", "ConfigurationException", False),
    165: ApiResponseCodeInfo(165, "Currency not supported", "Check the merchant account configuration in the portal. The MID's allowed currencies can be configured there. Additionally, check the value of PROCESSOR_RESPONSE in the", "ConfigurationException", False),
    170: ApiResponseCodeInfo(170, "Duplicate product amount and currency", "A product with matching properties already exists within the site.", "ConfigurationException", False),
    176: ApiResponseCodeInfo(176, "Duplicate product description and language", "A product with matching properties already exists within this Site", "ConfigurationException", False),
    180: ApiResponseCodeInfo(180, "Invalid transaction limit type", "The limit type was not recognized. Try using the portal to adjust velocity settings.", "ConfigurationException", False),
    181: ApiResponseCodeInfo(181, "Invalid limit type", "The limit type was not recognized. Try using the portal to adjust velocity settings.", "ConfigurationException", False),
    183: ApiResponseCodeInfo(183, "Payment Type is required", "Confirm that PMT_TYPE has been submitted, and has not been included multiple times.", "ConfigurationException", False),
    205: ApiResponseCodeInfo(205, "No Permissions on requested object", "You may not be able to check and confirm your own user permissions, so it may be necessary for an administrator to check them for you. If", "ConfigurationException", False),
    210: ApiResponseCodeInfo(210, "Merchant Account not found", "you feel this is an error, contact your administrator or Client Support. Verify the value of MERCH_ACCT_ID", "ConfigurationException", False),
    211: ApiResponseCodeInfo(211, "Currency not found", "The expected format is three-character currency code.", "ConfigurationException", False),
    215: ApiResponseCodeInfo(215, "Invalid Card Brand", "Check the card brand submitted. If you are certain it\u2019s correct, contact Client Support", "ConfigurationException", False),
    410: ApiResponseCodeInfo(410, "Field not supported with wallet payment", "Check the value of REF_FIELD in the response to see what incompatible element was", "ConfigurationException", True),
    411: ApiResponseCodeInfo(411, "REQUEST_CURRENCY mismatch with Cryptogram", "The currency in the gateway request needs to match the currency that was packed into the ApplePay cryptogram", "ConfigurationException", False),
    414: ApiResponseCodeInfo(414, "GooglePay token has expired", "", "ConfigurationException", False),
}


@dataclass(frozen=True)
class AvsCodeInfo:
    code: str
    description: str
    card_network: str
    #: DERIVED. 'partial' means some elements matched and some did not. Whether
    #: that is acceptable is a merchant risk-policy decision, not a spec fact.
    classification: str


AVS_CODES: Dict[str, AvsCodeInfo] = {
    "A": AvsCodeInfo("A", "Street address matches, but 5-digit and 9-digit postal code do not match.", "Standard domestic (US)", "partial"),
    "B": AvsCodeInfo("B", "Street address matches, but postal code not verified.", "Standard international", "neutral"),
    "C": AvsCodeInfo("C", "Street address and postal code do not match.", "Standard international", "negative"),
    "D": AvsCodeInfo("D", "Street address and postal code match. Code \"M\" is equivalent.", "Standard international", "positive"),
    "E": AvsCodeInfo("E", "AVS data is invalid or AVS is not allowed for this card type.", "Standard domestic (US)", "neutral"),
    "F": AvsCodeInfo("F", "Card member's name does not match, but billing postal code matches.", "American Express only", "partial"),
    "G": AvsCodeInfo("G", "Non-U.S. issuing bank does not support AVS.", "Standard international", "neutral"),
    "H": AvsCodeInfo("H", "Card member's name does not match. Street address and postal code match.", "American Express only", "partial"),
    "I": AvsCodeInfo("I", "Address not verified.", "Standard international", "neutral"),
    "J": AvsCodeInfo("J", "Card member's name, billing address, and postal code match.", "American Express only", "positive"),
    "K": AvsCodeInfo("K", "Card member's name matches but billing address and billing postal code do not match.", "American Express only", "partial"),
    "L": AvsCodeInfo("L", "Card member's name and billing postal code match, but billing address does not match.", "American Express only", "partial"),
    "M": AvsCodeInfo("M", "Street address and postal code match. Code \"D\" is equivalent.", "Standard international", "positive"),
    "N": AvsCodeInfo("N", "Street address and postal code do not match.", "Standard domestic (US)", "negative"),
    "O": AvsCodeInfo("O", "Card member's name and billing address match, but billing postal code does not match.", "American Express only", "partial"),
    "P": AvsCodeInfo("P", "Postal code matches, but street address not verified.", "Standard international", "neutral"),
    "Q": AvsCodeInfo("Q", "Card member's name, billing address, and postal code match.", "American Express only", "positive"),
    "R": AvsCodeInfo("R", "System unavailable.", "Standard domestic (US)", "neutral"),
    "S": AvsCodeInfo("S", "Bank does not support AVS.", "Standard domestic (US)", "neutral"),
    "T": AvsCodeInfo("T", "Card member's name does not match, but street address matches.", "American Express only", "partial"),
    "U": AvsCodeInfo("U", "Address information unavailable. Returned if the U.S. bank does not support non-U.S. AVS or if the AVS in a U.S. bank is not functioning properly.", "Standard domestic (US)", "neutral"),
    "V": AvsCodeInfo("V", "Card member's name, billing address, and billing postal code match.", "American Express only", "positive"),
    "W": AvsCodeInfo("W", "Street address does not match, but 9-digit postal code matches.", "Standard domestic (US)", "partial"),
    "X": AvsCodeInfo("X", "Street address and 9-digit postal code match.", "Standard domestic (US)", "positive"),
    "Y": AvsCodeInfo("Y", "Street address and 5-digit postal code match.", "Standard domestic (US)", "positive"),
    "Z": AvsCodeInfo("Z", "Street address does not match, but 5-digit postal code matches.", "Standard domestic (US)", "partial"),
}


@dataclass(frozen=True)
class CvvCodeInfo:
    code: str
    description: str
    classification: str


CVV_CODES: Dict[str, CvvCodeInfo] = {
    "M": CvvCodeInfo("M", "Match", "match"),
    "N": CvvCodeInfo("N", "No Match", "no_match"),
    "P": CvvCodeInfo("P", "Not Processed", "neutral"),
    "S": CvvCodeInfo("S", "Not Supported", "neutral"),
    "U": CvvCodeInfo("U", "Service Not Available", "neutral"),
    "X": CvvCodeInfo("X", "No CVC/CVV/CVV2/CID Response Data Available", "neutral"),
    "": CvvCodeInfo("", "No CVC/CVV/CVV2/CID Response Data Available", "neutral"),
}
