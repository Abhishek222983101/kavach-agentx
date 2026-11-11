"""Customer-facing replies (ARCH principle 6: facts from records, never from the model).

Every message that states money, dates, order state or policy is rendered here from verified fields, in the
customer's language: English, Hinglish (Roman Hindi) or Hindi (Devanagari). Short, warm, no jargon.

House style (like a real brand's support line): a *bold* first line that says the outcome, one or two short lines of
detail, an _italic_ "checked from records" line, and a reference number. Light markup only: *bold* and _italic_ are
native on WhatsApp, converted to HTML for Telegram, and rendered by the web chat.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")          # customers read dates in Indian time

Lang = str  # "en" | "hinglish" | "hi"


def rs(paise: int) -> str:
    r = paise // 100
    s = f"{r:,}"
    if r >= 100000:  # Indian grouping: 1,29,900
        head, tail = str(r)[:-3], str(r)[-3:]
        head = ",".join([head[max(0, i - 2):i] for i in range(len(head), 0, -2)][::-1])
        s = f"{head},{tail}"
    return f"₹{s}"


T: dict[str, dict[Lang, str]] = {
    "greeting": {
        "en": "Hi {name}! I'm Kavach, the shop's assistant. I can track an order, start a return, or sort out a refund. What do you need?",
        "hinglish": "Namaste {name}! Main Kavach hoon, shop ka assistant. Order track karna ho, return ya refund — bataiye kya madad karun?",
        "hi": "नमस्ते {name}! मैं कवच हूँ, दुकान का सहायक। ऑर्डर ट्रैक करना हो, रिटर्न या रिफ़ंड — बताइए क्या मदद करूँ?",
    },
    "choose_order": {
        "en": "*Which order is this about?*\n{options}\n\nReply with the number.",
        "hinglish": "*Kaunse order ki baat hai?*\n{options}\n\nNumber bhej dijiye.",
        "hi": "*किस ऑर्डर की बात है?*\n{options}\n\nनंबर भेज दीजिए।",
    },
    "no_orders": {
        "en": "I couldn't find any orders on your number.", "hinglish": "Aapke number par koi order nahi mila.",
        "hi": "आपके नंबर पर कोई ऑर्डर नहीं मिला।",
    },
    "not_yours": {
        "en": "Order {oid} isn't on your account, so I can't share its details.",
        "hinglish": "Order {oid} aapke account par nahi hai, isliye uski details share nahi kar sakta.",
        "hi": "ऑर्डर {oid} आपके अकाउंट पर नहीं है, इसलिए उसकी जानकारी नहीं दे सकता।",
    },
    "unknown_order": {
        "en": "I couldn't find order {oid}. Could you check the number?", "hinglish": "Order {oid} nahi mila. Number ek baar check karenge?",
        "hi": "ऑर्डर {oid} नहीं मिला। नंबर एक बार जाँच लेंगे?",
    },
    "status_delivered": {
        "en": "*Delivered* ✓\nYour {item} (order {oid}) was delivered on {date} ({days}).",
        "hinglish": "*Delivered* ✓\nAapka {item} (order {oid}) {date} ko deliver ho gaya tha ({days}).",
        "hi": "*डिलीवर हो गया* ✓\nआपका {item} (ऑर्डर {oid}) {date} को डिलीवर हो गया था ({days})।",
    },
    "status_transit": {
        "en": "*On the way* 🚚\nYour {item} (order {oid}) is with {courier}, last scanned at {where}. Expected in 1–2 days.",
        "hinglish": "*Raaste mein hai* 🚚\nAapka {item} (order {oid}) {courier} ke saath raaste mein hai, abhi {where} par. 1–2 din mein pahunch jayega.",
        "hi": "*रास्ते में है* 🚚\nआपका {item} (ऑर्डर {oid}) {courier} के साथ रास्ते में है, अभी {where} पर। 1–2 दिन में पहुँच जाएगा।",
    },
    "status_not_shipped": {
        "en": "*Not shipped yet*\nYour {item} (order {oid}) is {status}. You'll get the tracking details as soon as it's dispatched.",
        "hinglish": "*Abhi ship nahi hua*\nAapka {item} (order {oid}) abhi {status} hai, dispatch nahi hua. Dispatch hote hi tracking bhej denge.",
        "hi": "*अभी भेजा नहीं गया*\nआपका {item} (ऑर्डर {oid}) अभी {status} है। भेजते ही ट्रैकिंग की जानकारी मिल जाएगी।",
    },
    "courier_down": {
        "en": "The courier's system isn't responding right now. I've passed your question to the seller with the details.",
        "hinglish": "Courier ka system abhi jawab nahi de raha. Maine details ke saath seller ko bata diya hai.",
        "hi": "कूरियर का सिस्टम अभी जवाब नहीं दे रहा। मैंने जानकारी के साथ विक्रेता को बता दिया है।",
    },
    "need_photo": {
        "en": "*Sorry about that.* 📷\nPlease send a clear photo of the {item}, and I'll take it from there.\n_Our policy needs a photo for damaged or wrong items._",
        "hinglish": "*Maaf kijiye.* 📷\n{item} ki ek saaf photo bhej dijiye, phir main aage process kar dunga.\n_Policy: toote ya galat item ke liye photo zaroori hai._",
        "hi": "*माफ़ कीजिए।* 📷\n{item} की एक साफ़ फ़ोटो भेज दीजिए, फिर मैं आगे प्रोसेस कर दूँगा।\n_नियम: टूटे या गलत सामान के लिए फ़ोटो ज़रूरी है।_",
    },
    "photo_received": {
        "en": "Got the photo, thanks.", "hinglish": "Photo mil gayi, shukriya.", "hi": "फ़ोटो मिल गई, शुक्रिया।",
    },
    "done_refund": {
        "en": "*Done: refund approved* ✓\n{amount} for your {item} (order {oid}) is on its way to your {method}. It usually arrives in 5–7 working days.",
        "hinglish": "*Ho gaya: refund approved* ✓\n{item} (order {oid}) ka {amount} refund aapke {method} par bhej diya. 5–7 working days mein aa jayega.",
        "hi": "*हो गया: रिफ़ंड मंज़ूर* ✓\n{item} (ऑर्डर {oid}) का {amount} रिफ़ंड आपके {method} पर भेज दिया। 5–7 कार्य दिवसों में आ जाएगा।",
    },
    "done_return": {
        "en": "*Done: return pickup booked* ✓\nThe courier will collect your {item} (order {oid}) in 1–2 days. Please keep it packed.",
        "hinglish": "*Ho gaya: return pickup book* ✓\nCourier 1–2 din mein aapka {item} (order {oid}) le jayega. Item pack karke rakhiye.",
        "hi": "*हो गया: रिटर्न पिकअप बुक* ✓\nकूरियर 1–2 दिन में आपका {item} (ऑर्डर {oid}) ले जाएगा। सामान पैक करके रखिए।",
    },
    "done_address": {
        "en": "*Done: address updated* ✓\nOrder {oid} will now be delivered to:\n{address}",
        "hinglish": "*Ho gaya: address update* ✓\nOrder {oid} ab yahan deliver hoga:\n{address}",
        "hi": "*हो गया: पता बदल दिया* ✓\nऑर्डर {oid} अब यहाँ डिलीवर होगा:\n{address}",
    },
    "done_cancel": {
        "en": "*Done: order cancelled* ✓\nOrder {oid} ({item}) is cancelled.", "hinglish": "*Ho gaya: order cancel* ✓\nOrder {oid} ({item}) cancel kar diya.",
        "hi": "*हो गया: ऑर्डर रद्द* ✓\nऑर्डर {oid} ({item}) रद्द कर दिया।",
    },
    "escalated": {
        "en": "*Sent to the seller for approval* ⏳\nYour {what} for order {oid} checks out, but {why}, so the seller approves it personally. You'll hear back here.",
        "hinglish": "*Seller ke approval ke liye bheja* ⏳\nOrder {oid} ka {what} sahi hai, par {why}, isliye seller khud approve karenge. Jawab yahin aayega.",
        "hi": "*विक्रेता की मंज़ूरी के लिए भेजा* ⏳\nऑर्डर {oid} का {what} सही है, पर {why}, इसलिए विक्रेता ख़ुद मंज़ूरी देंगे। जवाब यहीं आएगा।",
    },
    "blocked": {
        "en": "*Sorry, I can't do this one*\nOrder {oid} ({item}): {why}.{clause}\n\nThink this is wrong? Reply *human* and the seller will take a look.",
        "hinglish": "*Maaf kijiye, ye nahi ho payega*\nOrder {oid} ({item}): {why}.{clause}\n\nLagta hai galat hai? *human* likhiye, seller khud dekhenge.",
        "hi": "*माफ़ कीजिए, यह नहीं हो पाएगा*\nऑर्डर {oid} ({item}): {why}।{clause}\n\nलगता है गलत है? *human* लिखिए, विक्रेता ख़ुद देखेंगे।",
    },
    "frozen": {
        "en": "*Paused for a moment*\nThe seller has paused refunds and changes for a while. Your request is noted and they'll get back to you.",
        "hinglish": "*Thodi der ke liye ruka hai*\nSeller ne abhi refunds aur changes thodi der ke liye rok diye hain. Aapki request note ho gayi hai, woh jaldi sampark karenge.",
        "hi": "विक्रेता ने अभी रिफ़ंड और बदलाव कुछ देर के लिए रोक दिए हैं। आपका अनुरोध दर्ज है, वे जल्द संपर्क करेंगे।",
    },
    "approved_done": {
        "en": "*Good news: the seller approved it* ✓\n{done}", "hinglish": "*Achhi khabar: seller ne approve kar diya* ✓\n{done}",
        "hi": "*अच्छी ख़बर: विक्रेता ने मंज़ूरी दे दी* ✓\n{done}",
    },
    "rejected": {
        "en": "The seller couldn't approve your {what} for order {oid}. They'll contact you if anything else is possible.",
        "hinglish": "Seller order {oid} ka {what} approve nahi kar paye. Kuch aur ho sakta ho to woh aapse sampark karenge.",
        "hi": "विक्रेता ऑर्डर {oid} का {what} मंज़ूर नहीं कर पाए। कुछ और संभव हुआ तो वे संपर्क करेंगे।",
    },
    "human": {
        "en": "*Connecting you to the seller* 🙋\nI've sent them a summary of our chat. They'll reply here.",
        "hinglish": "Bilkul. Maine seller ko hamari baat ka summary bhej diya hai, woh aapse sampark karenge.",
        "hi": "बिल्कुल। मैंने विक्रेता को हमारी बातचीत का सार भेज दिया है, वे आपसे संपर्क करेंगे।",
    },
    "policy": {
        "en": "Our policy: {text}", "hinglish": "Hamari policy: {text}", "hi": "हमारी नीति: {text}",
    },
    "other": {
        "en": "I can help with:\n• where your order is\n• returns and refunds\n• changing the address or cancelling\n\nWhat would you like to do?",
        "hinglish": "Main inme madad kar sakta hoon:\n• order kahan hai\n• return aur refund\n• address badalna ya cancel\n\nKya karna hai?",
        "hi": "मैं ऑर्डर स्टेटस, रिटर्न, रिफ़ंड, पता बदलने और कैंसल में मदद कर सकता हूँ। क्या करना है?",
    },
    "choose_reason": {
        "en": "*What happened with your {item}?* (order {oid})\n1. Arrived damaged\n2. Wrong item\n3. Never received it\n4. Changed my mind\n\nReply with the number.",
        "hinglish": "*{item} ke saath kya hua?* (order {oid})\n1. Toota/kharab aaya\n2. Galat item aaya\n3. Mila hi nahi\n4. Mann badal gaya\n\nNumber bhej dijiye.",
        "hi": "*{item} के साथ क्या हुआ?* (ऑर्डर {oid})\n1. टूटा/ख़राब आया\n2. गलत सामान आया\n3. मिला ही नहीं\n4. मन बदल गया\n\nनंबर भेज दीजिए।",
    },
    "busy": {
        "en": "We're getting a lot of messages right now. Please try again in a little while.",
        "hinglish": "Abhi bahut messages aa rahe hain. Thodi der baad try kijiye.",
        "hi": "अभी बहुत संदेश आ रहे हैं। थोड़ी देर बाद कोशिश कीजिए।",
    },
}

# plain-language reasons for a BLOCK, per failed check
WHY: dict[str, dict[Lang, str]] = {
    "ownership": {"en": "this order isn't on your account", "hinglish": "ye order aapke account par nahi hai", "hi": "यह ऑर्डर आपके अकाउंट पर नहीं है"},
    "state": {"en": "the order isn't in a state that allows this", "hinglish": "order abhi is stage mein nahi hai", "hi": "ऑर्डर अभी इस चरण में नहीं है"},
    "temporal": {"en": "it's past the {window}-day window ({days} days since delivery)", "hinglish": "{window} din ki window nikal gayi (delivery ko {days} din ho gaye)", "hi": "{window} दिन की अवधि निकल गई (डिलीवरी को {days} दिन हो गए)"},
    "monetary": {"en": "the amount is more than what can be refunded on this order", "hinglish": "amount is order par refund ho sakne wali rakam se zyada hai", "hi": "राशि इस ऑर्डर पर वापसी योग्य रकम से ज़्यादा है"},
    "duplicate": {"en": "a refund was already made on this order", "hinglish": "is order par refund pehle hi ho chuka hai", "hi": "इस ऑर्डर पर रिफ़ंड पहले ही हो चुका है"},
    "eligibility": {"en": "this item can't be returned (food and flowers are non-returnable)", "hinglish": "ye item return nahi hota (khane ka saamaan aur phool wapas nahi hote)", "hi": "यह सामान वापस नहीं होता (खाने का सामान और फूल वापस नहीं होते)"},
    "evidence_photo": {"en": "the photo doesn't show a damaged {item} (the photo check saw something else)", "hinglish": "photo mein toota {item} nahi dikh raha (photo check ko kuch aur dikha)", "hi": "फ़ोटो में टूटा {item} नहीं दिख रहा (फ़ोटो जाँच को कुछ और दिखा)"},
    "evidence": {"en": "a clear photo of the item is needed", "hinglish": "item ki saaf photo chahiye", "hi": "सामान की साफ़ फ़ोटो चाहिए"},
    "authority": {"en": "I can't act on \"the owner said so\": only the written policy counts", "hinglish": "\"owner ne bola\" par main kuch nahi kar sakta — sirf likhi hui policy maani jaati hai", "hi": "\"मालिक ने कहा\" पर मैं कुछ नहीं कर सकता — सिर्फ़ लिखी हुई नीति मानी जाती है"},
    "policy": {"en": "that's not what our policy says", "hinglish": "hamari policy aisa nahi kehti", "hi": "हमारी नीति ऐसा नहीं कहती"},
    "frequency": {"en": "too many refunds on this account recently", "hinglish": "is account par haal mein bahut refunds ho chuke hain", "hi": "इस अकाउंट पर हाल में बहुत रिफ़ंड हो चुके हैं"},
    "channel_identity": {"en": "this request must come from the phone number on the order", "hinglish": "ye request order wale number se aani chahiye", "hi": "यह अनुरोध ऑर्डर वाले नंबर से आना चाहिए"},
    "seller_rejected": {"en": "the seller declined it", "hinglish": "seller ne mana kar diya", "hi": "विक्रेता ने मना कर दिया"},
}

ESC_WHY: dict[str, dict[Lang, str]] = {
    "over_auto_limit": {"en": "it's above {limit}", "hinglish": "{limit} se zyada hai", "hi": "{limit} से ज़्यादा है"},
    "over_hard_cap": {"en": "it's a large amount", "hinglish": "bada amount hai", "hi": "बड़ी राशि है"},
    "refund_frequency": {"en": "you had another refund this month", "hinglish": "is mahine ek aur refund hua hai", "hi": "इस महीने एक और रिफ़ंड हुआ है"},
    "guard_flag": {"en": "the seller reviews requests like this", "hinglish": "aisi requests seller khud dekhte hain", "hi": "ऐसे अनुरोध विक्रेता ख़ुद देखते हैं"},
    "instruction_in_record": {"en": "the seller needs to take a look", "hinglish": "seller ko ek baar dekhna hoga", "hi": "विक्रेता को एक बार देखना होगा"},
    "photo_unverified": {"en": "the photo needs a quick look by a person", "hinglish": "photo ko ek baar seller dekhenge", "hi": "फ़ोटो को एक बार विक्रेता देखेंगे"},
}

WHAT: dict[str, dict[Lang, str]] = {
    "issue_refund": {"en": "{amount} refund", "hinglish": "{amount} refund", "hi": "{amount} रिफ़ंड"},
    "create_return_pickup": {"en": "return request", "hinglish": "return request", "hi": "रिटर्न अनुरोध"},
    "update_address": {"en": "address change", "hinglish": "address change", "hi": "पता बदलने का अनुरोध"},
    "cancel_order": {"en": "cancellation", "hinglish": "cancel request", "hi": "रद्द करने का अनुरोध"},
}


def say(key: str, lang: Lang, **kw) -> str:
    table = T[key]
    return table.get(lang, table["hinglish"]).format(**kw)


def phrase(table: dict[str, dict[Lang, str]], key: str, lang: Lang, **kw) -> str:
    entry = table.get(key)
    if not entry:
        return key.replace("_", " ")
    return entry.get(lang, entry["hinglish"]).format(**kw)


def days_ago(when: str | datetime | None, lang: Lang) -> tuple[str, str]:
    if not when:
        return "", ""
    dt = datetime.fromisoformat(when) if isinstance(when, str) else when
    d = max(0, (datetime.now(timezone.utc) - dt).days)
    date = dt.astimezone(IST).strftime("%d %b")
    rel = {"en": "today" if d == 0 else f"{d} day{'s' if d != 1 else ''} ago",
           "hinglish": "aaj" if d == 0 else f"{d} din pehle", "hi": "आज" if d == 0 else f"{d} दिन पहले"}
    return rel.get(lang, rel["hinglish"]), date


def records_line(order: dict, shipment: dict | None, lang: Lang, window_days: int = 7) -> str:
    """One visible line showing what was verified against the shop's records (the order record is the invoice)."""
    created = order.get("created_at")
    when = (datetime.fromisoformat(created) if isinstance(created, str) else created) if created else None
    ordered = when.astimezone(IST).strftime("%d %b") if when else "?"
    paid = rs(order["paid_paise"])
    method = "COD" if order.get("cod") else "UPI"
    parts = {"en": [f"ordered {ordered}", f"paid {paid} {method}"],
             "hinglish": [f"order {ordered}", f"{paid} {method} se paid"],
             "hi": [f"ऑर्डर {ordered}", f"{paid} {method} से भुगतान"]}.get(lang) or [f"order {ordered}", f"{paid} {method} se paid"]
    if shipment and shipment.get("status") == "delivered" and shipment.get("delivered_at"):
        at = shipment["delivered_at"]
        d = (datetime.now(timezone.utc) - (datetime.fromisoformat(at) if isinstance(at, str) else at)).days
        inside = d <= window_days
        parts.append({"en": f"delivered {d}d ago ({'inside' if inside else 'outside'} {window_days}-day window)",
                      "hi": f"{d} दिन पहले डिलीवर ({window_days} दिन की अवधि के {'अंदर' if inside else 'बाहर'})"}
                     .get(lang, f"{d} din pehle deliver ({window_days} din ki window ke {'andar' if inside else 'bahar'})"))
    label = {"en": "Checked from records", "hi": "रिकॉर्ड से जाँचा"}.get(lang, "Records se check kiya")
    return f"\n\n_{label}: " + " · ".join(parts) + "_"


WEB = os.getenv("PUBLIC_WEB_URL", "https://kavach-agentx.vercel.app").rstrip("/")


def ref_line(trace_id: str | None, channel: str, lang: Lang) -> str:
    """Reference number on every decision; phones also get the receipt link (anyone can verify what was checked)."""
    if not trace_id:
        return ""
    ref = "K-" + trace_id[-6:].upper()
    label = {"en": "Ref", "hi": "संदर्भ"}.get(lang, "Ref")
    if channel == "web":
        return f"\n\n{label} {ref}"
    return f"\n\n{label} {ref} · receipt: {WEB}/proof/{trace_id}"


def policy_quote(clause: dict, lang: Lang) -> str:
    text = clause["text_hinglish"] if lang == "hinglish" and clause.get("text_hinglish") else clause["text"]
    label = {"en": "Shop policy", "hi": "दुकान की नीति"}.get(lang, "Shop policy")
    return f"\n_{label}: \"{text}\"_"


def greeting(name: str, orders: list[dict], lang: Lang) -> str:
    """Warm, short, and useful: mention the order the customer most likely cares about, then what we can do."""
    first = (name or "").split(" ")[0]
    first = "" if first.lower() in ("demo", "customer", "") else first
    moving = next((o for o in orders if o.get("status") == "shipped"), None)
    hello = {"en": f"Hi{(' ' + first) if first else ''}! 👋 I'm Kavach, the shop's support assistant.",
             "hi": f"नमस्ते{(' ' + first) if first else ''}! 👋 मैं कवच हूँ, दुकान का सहायक।"}.get(
        lang, f"Namaste{(' ' + first) if first else ''}! 👋 Main Kavach hoon, shop ka support assistant.")
    heads = ""
    if moving:
        heads = {"en": f"\nGood news: your *{moving['item']}* order is on the way.", "hi": f"\nआपका *{moving['item']}* ऑर्डर रास्ते में है।"}.get(
            lang, f"\nAapka *{moving['item']}* order raaste mein hai.")
    menu = {"en": "\n\nI can help you:\n• track an order\n• return or refund an item\n• change the address or cancel\n\nJust type what you need, in English, Hinglish or Hindi.",
            "hi": "\n\nमैं इनमें मदद कर सकता हूँ:\n• ऑर्डर ट्रैक करना\n• रिटर्न या रिफ़ंड\n• पता बदलना या कैंसल\n\nजो चाहिए, लिख दीजिए।"}.get(
        lang, "\n\nMain inme madad kar sakta hoon:\n• order track karna\n• return ya refund\n• address badalna ya cancel\n\nJo chahiye, likh dijiye: English, Hinglish ya Hindi.")
    return hello + heads + menu


def refund_status(refunds: list[dict], orders: list[dict], order_id: int | None, lang: Lang) -> str:
    """'Where is my refund?' answered from the refund records, with the expected arrival date."""
    names = {o["id"]: o["item"] for o in orders}
    rows = [r for r in refunds if order_id is None or r.get("order_id") == order_id]
    if not rows:
        if order_id:
            return {"en": f"*No refund yet on order {order_id}*\nNothing has been refunded on this order so far. Want me to look into it? Tell me what went wrong.",
                    "hi": f"*ऑर्डर {order_id} पर अभी कोई रिफ़ंड नहीं*\nइस ऑर्डर पर अब तक कोई रिफ़ंड नहीं हुआ। क्या दिक़्क़त है, बताइए।"}.get(
                lang, f"*Order {order_id} par abhi koi refund nahi*\nIs order par ab tak koi refund nahi hua. Kya dikkat hai, bataiye.")
        return {"en": "*No refunds on your account yet*\nIf something went wrong with an order, tell me which one.",
                "hi": "*आपके अकाउंट पर अभी कोई रिफ़ंड नहीं*\nकिसी ऑर्डर में दिक़्क़त हो तो बताइए।"}.get(
            lang, "*Aapke account par abhi koi refund nahi*\nKisi order mein dikkat ho to bataiye.")
    lines = []
    for r in rows[:3]:
        at = r.get("created_at")
        dt = datetime.fromisoformat(at) if isinstance(at, str) else at
        sent, eta = (dt.astimezone(IST).strftime("%d %b"), (dt + timedelta(days=7)).astimezone(IST).strftime("%d %b")) if dt else ("?", "?")
        item = names.get(r.get("order_id"), f"order {r.get('order_id')}")
        lines.append({"en": f"• {rs(r['amount_paise'])} for {item}: sent {sent}, arrives by {eta}",
                      "hi": f"• {item} का {rs(r['amount_paise'])}: {sent} को भेजा, {eta} तक आ जाएगा"}.get(
            lang, f"• {item} ka {rs(r['amount_paise'])}: {sent} ko bheja, {eta} tak aa jayega"))
    head = {"en": "*Your refunds*", "hi": "*आपके रिफ़ंड*"}.get(lang, "*Aapke refunds*")
    tail = {"en": "\n_Banks take 5–7 working days. Write \"human\" if it's later than that._",
            "hi": "\n_बैंक 5–7 कार्य दिवस लेते हैं। देर हो तो \"human\" लिखिए।_"}.get(
        lang, "\n_Bank 5–7 working days lete hain. Der ho to \"human\" likhiye._")
    return head + "\n" + "\n".join(lines) + tail
