"""Customer-facing replies (ARCH principle 6: facts from records, never from the model).

Every message that states money, dates, order state or policy is rendered here from verified fields, in the
customer's language: English, Hinglish (Roman Hindi) or Hindi (Devanagari). Short, warm, no jargon.
"""
from __future__ import annotations

from datetime import datetime, timezone

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
        "en": "Which order is this about?\n{options}\nReply with the number.",
        "hinglish": "Kaunse order ki baat hai?\n{options}\nNumber bhej dijiye.",
        "hi": "किस ऑर्डर की बात है?\n{options}\nनंबर भेज दीजिए।",
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
        "en": "Your {item} (order {oid}) was delivered {days} on {date}.",
        "hinglish": "Aapka {item} (order {oid}) {date} ko deliver ho gaya tha ({days}).",
        "hi": "आपका {item} (ऑर्डर {oid}) {date} को डिलीवर हो गया था ({days})।",
    },
    "status_transit": {
        "en": "Your {item} (order {oid}) is on the way with {courier}: last seen at {where}. It should reach you in 1–2 days.",
        "hinglish": "Aapka {item} (order {oid}) {courier} ke saath raaste mein hai — abhi {where} par hai. 1–2 din mein pahunch jayega.",
        "hi": "आपका {item} (ऑर्डर {oid}) {courier} के साथ रास्ते में है — अभी {where} पर है। 1–2 दिन में पहुँच जाएगा।",
    },
    "status_not_shipped": {
        "en": "Your {item} (order {oid}) is {status} and hasn't been dispatched yet.",
        "hinglish": "Aapka {item} (order {oid}) abhi {status} hai, dispatch nahi hua.",
        "hi": "आपका {item} (ऑर्डर {oid}) अभी {status} है, भेजा नहीं गया।",
    },
    "courier_down": {
        "en": "The courier's system isn't responding right now. I've passed your question to the seller with the details.",
        "hinglish": "Courier ka system abhi jawab nahi de raha. Maine details ke saath seller ko bata diya hai.",
        "hi": "कूरियर का सिस्टम अभी जवाब नहीं दे रहा। मैंने जानकारी के साथ विक्रेता को बता दिया है।",
    },
    "need_photo": {
        "en": "Sorry about that! Please send a clear photo of the {item} so I can process it (policy: damaged items need a photo).",
        "hinglish": "Maaf kijiye! {item} ki ek saaf photo bhej dijiye, phir main process kar dunga (policy: toote item ke liye photo zaroori hai).",
        "hi": "माफ़ कीजिए! {item} की एक साफ़ फ़ोटो भेज दीजिए, फिर मैं प्रोसेस कर दूँगा (नियम: टूटे सामान के लिए फ़ोटो ज़रूरी है)।",
    },
    "photo_received": {
        "en": "Got the photo, thanks.", "hinglish": "Photo mil gayi, shukriya.", "hi": "फ़ोटो मिल गई, शुक्रिया।",
    },
    "done_refund": {
        "en": "Done ✅ {amount} refund for your {item} (order {oid}). It reaches your {method} in 5–7 working days.",
        "hinglish": "Ho gaya ✅ {item} (order {oid}) ka {amount} refund kar diya. 5–7 working days mein aapke {method} par aa jayega.",
        "hi": "हो गया ✅ {item} (ऑर्डर {oid}) का {amount} रिफ़ंड कर दिया। 5–7 कार्य दिवसों में आपके {method} पर आ जाएगा।",
    },
    "done_return": {
        "en": "Done ✅ Return pickup booked for your {item} (order {oid}). The courier will collect it in 1–2 days.",
        "hinglish": "Ho gaya ✅ {item} (order {oid}) ka return pickup book ho gaya. Courier 1–2 din mein le jayega.",
        "hi": "हो गया ✅ {item} (ऑर्डर {oid}) का रिटर्न पिकअप बुक हो गया। कूरियर 1–2 दिन में ले जाएगा।",
    },
    "done_address": {
        "en": "Done ✅ The delivery address for order {oid} is now: {address}",
        "hinglish": "Ho gaya ✅ Order {oid} ka naya address: {address}",
        "hi": "हो गया ✅ ऑर्डर {oid} का नया पता: {address}",
    },
    "done_cancel": {
        "en": "Done ✅ Order {oid} ({item}) is cancelled.", "hinglish": "Ho gaya ✅ Order {oid} ({item}) cancel kar diya.",
        "hi": "हो गया ✅ ऑर्डर {oid} ({item}) रद्द कर दिया।",
    },
    "escalated": {
        "en": "I've sent your {what} for order {oid} to the seller for approval ({why}). You'll get a message here as soon as they decide.",
        "hinglish": "Order {oid} ka {what} seller ko approval ke liye bhej diya hai ({why}). Jaise hi woh decide karenge, yahin message aa jayega.",
        "hi": "ऑर्डर {oid} का {what} विक्रेता को मंज़ूरी के लिए भेज दिया है ({why})। जैसे ही वे फ़ैसला करेंगे, यहीं संदेश आ जाएगा।",
    },
    "blocked": {
        "en": "Order {oid} ({item}): I can't do this one: {why}{clause}\nIf you think this is wrong, reply \"human\" and I'll ask the seller.",
        "hinglish": "Order {oid} ({item}): ye nahi ho payega — {why}{clause}\nAgar aapko lagta hai ye galat hai, \"human\" likhiye, main seller se poochh lunga.",
        "hi": "ऑर्डर {oid} ({item}): यह नहीं हो पाएगा — {why}{clause}\nअगर आपको लगता है यह गलत है, \"human\" लिखिए, मैं विक्रेता से पूछ लूँगा।",
    },
    "frozen": {
        "en": "The seller has paused refunds and changes for a while. Your request is noted and they'll get back to you.",
        "hinglish": "Seller ne abhi refunds aur changes thodi der ke liye rok diye hain. Aapki request note ho gayi hai, woh jaldi sampark karenge.",
        "hi": "विक्रेता ने अभी रिफ़ंड और बदलाव कुछ देर के लिए रोक दिए हैं। आपका अनुरोध दर्ज है, वे जल्द संपर्क करेंगे।",
    },
    "approved_done": {
        "en": "Good news: the seller approved it ✅ {done}", "hinglish": "Achhi khabar: seller ne approve kar diya ✅ {done}",
        "hi": "अच्छी ख़बर: विक्रेता ने मंज़ूरी दे दी ✅ {done}",
    },
    "rejected": {
        "en": "The seller couldn't approve your {what} for order {oid}. They'll contact you if anything else is possible.",
        "hinglish": "Seller order {oid} ka {what} approve nahi kar paye. Kuch aur ho sakta ho to woh aapse sampark karenge.",
        "hi": "विक्रेता ऑर्डर {oid} का {what} मंज़ूर नहीं कर पाए। कुछ और संभव हुआ तो वे संपर्क करेंगे।",
    },
    "human": {
        "en": "Sure. I've asked the seller to get back to you, with a summary of our chat.",
        "hinglish": "Bilkul. Maine seller ko hamari baat ka summary bhej diya hai, woh aapse sampark karenge.",
        "hi": "बिल्कुल। मैंने विक्रेता को हमारी बातचीत का सार भेज दिया है, वे आपसे संपर्क करेंगे।",
    },
    "policy": {
        "en": "Our policy: {text}", "hinglish": "Hamari policy: {text}", "hi": "हमारी नीति: {text}",
    },
    "other": {
        "en": "I can help with order status, returns, refunds, address changes and cancellations. What would you like to do?",
        "hinglish": "Main order status, return, refund, address change aur cancel mein madad kar sakta hoon. Kya karna hai?",
        "hi": "मैं ऑर्डर स्टेटस, रिटर्न, रिफ़ंड, पता बदलने और कैंसल में मदद कर सकता हूँ। क्या करना है?",
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
    date = dt.strftime("%d %b")
    rel = {"en": "today" if d == 0 else f"{d} day{'s' if d != 1 else ''} ago",
           "hinglish": "aaj" if d == 0 else f"{d} din pehle", "hi": "आज" if d == 0 else f"{d} दिन पहले"}
    return rel.get(lang, rel["hinglish"]), date
