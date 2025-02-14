
"""База знаний бота с переводами."""
from chats.db.mongo.schemas import BriefQuestion


BRIEF_QUESTIONS = [
    BriefQuestion(
        question="Hello! Thank you for contacting PaNa Medica. May I have your name?",
        question_translations={
            "en": "Hello! Thank you for contacting PaNa Medica. May I have your name?",
            "ru": "Здравствуйте! Благодарим вас за обращение в PaNa Medica. Подскажите, как вас зовут?",
            "pl": "Dzień dobry! Dziękujemy za kontakt z PaNa Medica. Jak się Pan/Pani nazywa?",
            "uk": "Вітаємо! Дякуємо, що звернулися до PaNa Medica. Як Вас звати?",
            "ge": "გამარჯობა! გმადლობთ, რომ დაგვიკავშირდით PaNa Medica-სთან. რა გქვიათ?"
        },
        question_type="text"
    ),
    BriefQuestion(
        question="Are you currently in or near Warsaw, or are you located elsewhere?",
        question_translations={
            "en": "Are you currently in or near Warsaw, or are you located elsewhere?",
            "ru": "Вы сейчас в Варшаве (или рядом) или находитесь в другом городе?",
            "pl": "Czy jest Pan/Pani obecnie w Warszawie lub w pobliżu, czy w innym miejscu?",
            "uk": "Ви зараз у Варшаві (або поблизу) чи перебуваєте в іншому місті?",
            "ge": "ახლა ვარშავაში ხართ (ან მის ახლოს) თუ სხვა ქალაქში იმყოფებით?"
        },
        question_type="choice",
        expected_answers=["Local", "Visiting / Tourist"],
        expected_answers_translations={
            "en": ["Local", "Visiting / Tourist"],
            "ru": ["Местный", "Приезжий / Турист"],
            "pl": ["Lokalny", "Przyjezdny / Turysta"],
            "uk": ["Місцевий", "Приїжджий / Турист"],
            "ge": ["ადგილობრივი", "მოგზაური / ტურისტი"]
        }
    ),
    BriefQuestion(
        question="Could you please briefly describe your dental issue?",
        question_translations={
            "en": "Could you please briefly describe your dental issue?",
            "ru": "Расскажите, пожалуйста, кратко, что у вас с зубами?",
            "pl": "Czy może Pan/Pani krótko opisać swój problem stomatologiczny?",
            "uk": "Чи можете ви коротко описати свою стоматологічну проблему?",
            "ge": "შეგიძლიათ მოკლედ აგვიხსნათ თქვენი სტომატოლოგიური პრობლემა?"
        },
        question_type="text"
    )
]


KNOWLEDGE_BASE = {
    "General Information 🌐": {
        "subtopics": {
            "Bot Role & Company Info 📋": {
                "questions": {
                    "What is the chatbot’s role?": (
                        "I am a call-center consultant for PaNa Medica with sales elements. "
                        "My goal is to imitate a real person’s communication style, provide accurate information "
                        "about our dental services, and ultimately guide patients to schedule a visit or arrange "
                        "an online consultation if they live far from Warsaw."
                    ),
                    "What is the company name?": (
                        "Our clinic is called PaNa Medica."
                    ),
                    "What are the chatbot’s main responsibilities?": (
                        "1) Provide text-based consultations.\n"
                        "2) Eventually handle voice interactions (future expansion).\n"
                        "3) Offer professional advice on all clinic services.\n"
                        "4) Ask clarifying questions to help determine the proper treatment or specialist.\n"
                        "5) Aim to schedule the patient for an in-clinic visit (or online consultation if they’re not local).\n"
                        "6) Provide a clear summary to the live admin for booking.\n"
                        "7) In the future, handle direct scheduling in our CRM based on internal rules."
                    ),
                    "Where do leads go?": (
                        "Stage 1: The chatbot collects patient details and forwards them to a live manager.\n"
                        "Stage 2 (planned): direct booking in our own CRM system (IP open)."
                    ),
                    "What is the clinic contact information?": (
                        "Phone: +48 511 111 595 (all messengers available)\n"
                        "Telegram: @Panamedwaw\n"
                        "Instagram & Facebook: pa_na_medica\n"
                        "Working hours: 24/7"
                    ),
                    "How to handle situations the bot cannot resolve?": (
                        "If the bot is unsure how to assist, it should give the contact: +48 511 111 595.\n"
                        "A live specialist will handle any complex queries."
                    ),
                    "Which CRM system is used?": (
                        "We plan to integrate with our own custom CRM solution."
                    ),
                    "What is the chatbot’s tone of voice?": (
                        "Friendly, welcoming, polite, and professional. The bot addresses patients formally (using polite forms)."
                    ),
                    "Which platforms is the bot integrated with?": (
                        "Instagram, Telegram, Facebook, WhatsApp, Viber."
                    )
                }
            }
        }
    },
    "Administrative & Procedures": {
        "subtopics": {
            "Booking & Registration": {
                "questions": {
                    "What data is required to schedule a new patient appointment?": (
                        "For new patients, the chatbot must collect the patient’s first name and last name "
                        "(in Latin characters), a contact phone number, and (if available) a PESEL number. "
                        "If the patient provides personal data in the chat, they thereby agree to our privacy policy "
                        "(available at pa-na.pl)."
                    ),
                    "How can a new patient receive an e-referral for a CBCT scan?": (
                        "To issue an e-referral, we must have the patient’s PESEL, full name in Latin characters, "
                        "and registered address. If the patient does not have a PESEL, we cannot create an e-referral. "
                        "In that case, the patient must either come to our clinic for a paper referral or receive "
                        "a photo of the paper referral via email if they reside in another city or abroad. "
                        "Often, this photo is sufficient for local imaging centers."
                    )
                }
            },
            "Complaints & Reworks": {
                "questions": {
                    "What if a temporary crown you placed has fallen out?": (
                        "The temporary crown should be reattached as soon as possible, at no charge. "
                        "We ask the patient when the crown was placed and by which doctor. Then we forward this info, "
                        "along with the patient’s name (in Latin), to the registry for scheduling."
                    ),
                    "What if a crown has fallen off, but I am not sure if you placed it?": (
                        "We ask whether the crown was placed in our clinic or elsewhere. If it was placed here, "
                        "we confirm when it was placed and by which doctor, and note the patient’s full name (in Latin). "
                        "If the crown or bridge is from another clinic, we ask:\n"
                        "1) Did the crown fall out with a post inside it or separately? Is the tooth in the mouth "
                        "intact or destroyed?\n"
                        "2) Does the patient have an x-ray or photos of the fallen crown/bridge?\n"
                        "We explain that to properly re-cement, we must ensure the tooth underneath is suitable. "
                        "We may require an x-ray (or CBCT if it’s a bridge) to check root canal fillings and tooth integrity. "
                        "If canals are poorly sealed, we must retreat them before re-cementing. "
                        "If the tooth is severely damaged, it may need extraction. "
                        "The cost of re-cementing one external crown from another clinic is about 300 PLN, "
                        "assuming everything else is in good condition. Bridges are calculated based on each supporting crown. "
                        "Additional treatments (x-rays, canal retreatment, tooth restoration) are extra."
                    ),
                    "How to avoid conflicting messages when info is passed to the administrator?": (
                        "Once the chatbot has forwarded patient information to the registration desk or administrator, "
                        "it should inform the patient that a live administrator has the details and is following up. "
                        "If the administrator takes too long to respond and the patient messages again, "
                        "the chatbot will remind the administrator. This prevents conflicting or duplicate communications."
                    )
                }
            },
            "Additional Info & Resources": {
                "questions": {
                    "Where can I find your official website and Instagram page?": (
                        "Our official website is https://pa-na.pl/pl/\n"
                        "Our Instagram page is https://www.instagram.com/pa_na_medica?igsh=MXZhaHR1bDBsZzExZg==\n"
                        "Feel free to explore both for more details, photos, and updates."
                    ),
                    "What can your chatbot do?": (
                        "Our chatbot can provide initial information about treatments, pricing, and clinic protocols, "
                        "ask clarifying questions to determine your needs, and then either guide you to a live administrator "
                        "for booking or schedule an appointment directly once integrated with our CRM system."
                    )
                }
            },
        },
    },
    "Clinic Services 🦷": {
        "subtopics": {
            "Visiting Patients (Algorithm) 🛬": {
                "questions": {
                    "What is the process for patients coming from abroad or far from Warsaw?": (
                        "If the chatbot identifies that the patient is not from Poland or is located far from Warsaw, "
                        "it should first clarify what the patient’s concern is, what they want to accomplish, and how urgent it is. "
                        "We offer a 40-minute online consultation for such patients at a cost of 200 PLN or 50 EUR. "
                        "If the patient is interested in an online consultation, the bot asks if they have any x-rays. "
                        "If they do, they can send them to pana@pa-na.pl. "
                        "If not, we suggest getting an x-ray locally (we can provide a referral), then taking several photographs: "
                        "1) Face at rest (frontal) with teeth together, "
                        "2) Face smiling, "
                        "3) Face with a wide grin, "
                        "4) Upper teeth, "
                        "5) Lower teeth, "
                        "6) Side views with the cheek retracted so the teeth are visible. "
                        "All images and the x-ray should then be sent to pana@pa-na.pl. "
                        "The patient must pre-pay the online consultation in any currency to our account. "
                        "After the online consultation, the doctor and administrators will guide the patient further."
                    )
                }
            },
            "Crowns and Bridges": {
                "questions": {
                    "How do you manufacture zirconia crowns and bridges?": (
                        "We produce crowns and bridges from zirconium dioxide (“zirconia”). "
                        "If the tooth is already properly treated (root canals done and the visible part of the tooth above the gum restored correctly), "
                        "the fabrication process can be done quickly. From the moment we take impressions or scans, we can finish crowns and bridges "
                        "in as little as two days—e.g., scanning in the morning and installing the finished restorations the next evening. "
                        "Standard production time is about five working days. There are typically two visits: "
                        "the first for taking impressions or scans, and the second for placing the final crowns/bridges. "
                        "If there are complications (poorly treated canals or insufficient tooth structure), "
                        "additional preliminary treatment may be needed, which affects pricing. "
                        "That is why a consultation (in-person or online for visiting patients) with x-rays is always recommended first."
                    )
                }
            },
            "Emax Veneers": {
                "questions": {
                    "What is the process for Emax veneers?": (
                        "We also manufacture ceramic veneers from Emax, known for their excellent strength and esthetics. "
                        "1) On the first visit, we scan the jaws and photograph the patient’s face to create a 3D project. "
                        "2) On the second visit, we discuss the computer-designed project of the future teeth. We finalize all details and pricing. "
                        "If the patient dislikes something, we adjust the project before proceeding. "
                        "3) The third step is the actual tooth preparation under a microscope, usually limited to the enamel. "
                        "If minimal thickness is required (0.2–0.4 mm), sometimes no preparation is needed. "
                        "We then take impressions or scans, and place temporary veneers made from a composite material that mimic the final shape. "
                        "If something needs changing, it’s corrected on these temporaries. "
                        "4) The fourth step is trying in and bonding the permanent veneers, typically about 4–5 working days after the third step. "
                        "The average cost for one ceramic veneer, including photo documentation, 3D planning, and temporaries, is about 3300 PLN."
                    )
                }
            },
            "Metal-ceramic vs Zirconia Crowns": {
                "questions": {
                    "What is the difference between metal-ceramic and zirconia crowns?": (
                        "Metal-ceramic crowns have a metal base covered externally by ceramic. Metal can sometimes cause allergic reactions. "
                        "A common issue is at the crown margin near the gum, where the gum does not adhere as well, potentially leading to secondary decay and a dark gum line. "
                        "Zirconia crowns do not have that issue because polished zirconia allows the gum to ‘seal’ closely, prolonging the lifespan of both the crown and the underlying tooth."
                    )
                }
            },
            "Types of Prostheses": {
                "questions": {
                    "What types of prostheses do you offer?": (
                        "Non-removable restorations: zirconia and all-ceramic crowns/bridges (including on implants), ceramic inlays, and veneers. "
                        "Removable restorations: partial or full dentures, which may be less comfortable. "
                        "We also offer framework (partial) dentures (‘bugel’ type) that occupy less space in the mouth. "
                        "Conditionally removable restorations on a bar attachment are used when all teeth are missing. "
                        "They remain stable during chewing but can be removed if needed. "
                        "AllOn4 or AllOn6 solutions are ‘fixed’ restorations supported by 4 or 6 implants, typically not removed daily. "
                        "Temporary prostheses (crowns, veneers, or dentures) are used during the transition to permanent restorations."
                    )
                }
            },
            "Implants & Implant-based Prosthetics": {
                "questions": {
                    "How does implant-based prosthetics work?": (
                        "It starts with a CBCT scan and consultation with a prosthodontist and implant surgeon. "
                        "The prosthodontist plans the future restoration and examines adjacent teeth. "
                        "The surgeon checks overall health and bone condition. If conditions are good, the implant is placed, "
                        "stitches are made, and removed after about 10 days. The waiting period is typically 3–4 months for osseointegration. "
                        "Around two months post-surgery, a panoramic x-ray is taken to assess integration. "
                        "After 3–4 months, the surgeon attaches a healing abutment (FDM) to shape the gum. "
                        "Then, after ~10 days, prosthetic work can begin, taking an additional 2–5 working days to fabricate the zirconia crown. "
                        "We do not use metal-ceramic on implants because zirconia and titanium allow the gum to seal more effectively."
                    ),
                    "Do you handle implants placed elsewhere?": (
                        "Yes. We need a panoramic x-ray showing successful integration and the implant passport with its specifications. "
                        "We must also have compatible transfer components to take impressions. If we have them, standard protocols apply. "
                        "If we need to buy a new component, the patient covers its cost (about 250–300 PLN). "
                        "Otherwise, the cost follows our usual price list."
                    ),
                    "Which implants do you use?": (
                        "We primarily use Korean Megagen AnyRige implants, which are premium quality with an excellent "
                        "price-to-performance ratio (~99% integration success). We also offer German Straumann implants "
                        "(about 3900 PLN), which some patients specifically request."
                    ),
                    "What is an implant (dental implant)?": (
                        "A dental implant replaces the root of a missing tooth. On x-rays, it looks like a screw set into the bone. "
                        "Later, a crown is placed on top. Implants can be placed after a tooth is extracted or immediately "
                        "during the same visit, if the conditions are appropriate."
                    ),
                    "Immediate vs. delayed implant placement?": (
                        "Option 1 (delayed): remove the tooth, wait ~4 months for bone healing, then place the implant, wait ~3 more "
                        "months for integration, and finally place the crown. Sometimes additional bone-grafting procedures "
                        "extend treatment by several more months. \n\n"
                        "Option 2 (immediate): if there is sufficient bone and minimal inflammation, the tooth can be removed "
                        "and the implant placed right away. Then in ~3 months the bone integrates around the implant, "
                        "and the crown can be installed. This approach can reduce total treatment time from a year or more "
                        "down to about 4 months."
                    ),
                    "What about using implants from other manufacturers?": (
                        "We can place crowns on implants placed at other clinics. We need:\n"
                        "1) An x-ray confirming successful integration.\n"
                        "2) The implant passport (brand, diameter, platform, etc.).\n\n"
                        "If we have all necessary components for that implant system, the cost is typically 2950 PLN for a zirconia crown. "
                        "If we need to purchase special parts (transfers, abutments), the patient covers that cost (about 250 PLN each)."
                    ),
                    "Do you guarantee the implant and crown?": (
                        "We guarantee procedures done entirely in our clinic (both implant placement and crown). "
                        "If the implant was placed elsewhere and we only attach the crown, our warranty covers the crown alone, "
                        "but not the implant’s integration or performance in the bone."
                    )
                }
            },
            "Emergency Cases & Broken Teeth": {
                "questions": {
                    "What if a filling falls out or a tooth breaks?": (
                        "First, the bot asks if the tooth or filling was originally treated in our clinic. If yes, we check when it was done "
                        "and note the patient’s full name (in Latin). Then we forward the info to the registry. "
                        "If it was not our work, we ask if the tooth hurts, how it hurts (cold/hot, constant throbbing, etc.), "
                        "and whether the patient has any x-rays. We then pass all that info to the administrator to arrange an appropriate specialist."
                    )
                }
            },
            "Consultation & Price Inquiries": {
                "questions": {
                    "If I want multiple veneers or crowns, can you give me a price upfront?": (
                        "We recommend a CBCT scan (either existing or done at our clinic) and an in-person consultation. "
                        "Exact pricing depends on the condition of adjacent teeth, previous treatments, and the patient’s desired outcome. "
                        "Only after seeing the patient or their scan can we provide a more accurate quote."
                    )
                }
            },
            "Pricing Details": {
                "questions": {
                    "What is the cost of caries treatment?": (
                        "For small to moderate cavities, it’s about 450–550 PLN. If the tooth is more severely damaged "
                        "and requires a medicated base, the cost can be 550–800 PLN. "
                        "Front tooth restorations can cost 80–150 PLN more for aesthetic work."
                    ),
                    "What about root canal treatment costs?": (
                        "For a tooth that has never had root canals treated before, each canal is 600–750 PLN on average, "
                        "depending on difficulty and access. A tooth may have 1 to 5+ canals. "
                        "Retreatment (secondary endodontics) can be 700–1200 PLN per canal, due to complexity. "
                        "We always use a microscope and modern materials. Final cost is confirmed once the dentist examines the tooth and x-ray."
                    ),
                    "How much do crowns and veneers cost?": (
                        "A temporary crown is 350 PLN. A permanent zirconia crown on a prepared tooth in posterior areas is 2450 PLN. "
                        "In the esthetic zone (canine to canine), a zirconia crown costs 2950 PLN. "
                        "A zirconia implant crown in posterior areas is 2950 PLN, while in the esthetic zone it can reach 4000 PLN, "
                        "depending on complexity. Composite (direct) veneer is ~1100 PLN. A ceramic veneer is ~3200 PLN including photo protocol "
                        "and 3D modeling. Any additional procedures (restoration, canal treatment) are extra."
                    ),
                    "Is a CBCT scan needed for consultation?": (
                        "We prefer having a CBCT scan for a thorough assessment, which costs 310 PLN in our clinic. "
                        "It allows the doctor to evaluate all teeth and surrounding bone structure."
                    )
                }
            },
            "Whitening": {
                "questions": {
                    "Do you offer teeth whitening?": (
                        "We use a professional dental lamp that modifies the enamel structure rather than weakening it, "
                        "minimizing sensitivity. The package includes in-office laser whitening plus custom trays for at-home touch-ups. "
                        "The cost is 2500 PLN."
                    )
                }
            },
            "Professional Cleaning": {
                "questions": {
                    "What does a professional cleaning include?": (
                        "It involves ultrasonic removal of supra- and subgingival tartar, air polishing to remove debris, "
                        "polishing, fluoride treatment, and hygiene instruction. The total cost is 390 PLN."
                    )
                }
            },
            "Orthodontics": {
                "questions": {
                    "Do you offer braces or aligners?": (
                        "Yes, we have an orthodontist who can provide metal braces (visible brackets and wires) or clear removable aligners. "
                        "Braces start from 3900 PLN per arch, aligners from 4500 PLN per arch. "
                        "Exact cost and duration depend on the case, as determined at consultation."
                    )
                }
            },
            "Wisdom Teeth Removal": {
                "questions": {
                    "How do you handle impacted wisdom teeth or extractions?": (
                        "We require a CBCT scan to assess root shape and proximity to nerves or sinuses. "
                        "At the consultation, the surgeon discusses risks, any needed medication, and schedules the procedure. "
                        "We use an ultrasonic device to preserve bone and soft tissue, reducing recovery time. "
                        "Extraction can cost 600–1400+ PLN, depending on complexity. The exact amount is explained at consultation."
                    )
                }
            },
            "Tooth Extraction": {
                "questions": {
                    "What about routine tooth extractions?": (
                        "Simple extractions start from 400–500 PLN, potentially up to ~800 PLN for multi-root teeth "
                        "requiring segmentation to preserve bone. If the patient plans an implant later, "
                        "we recommend a CBCT before extraction. Sometimes the tooth can be removed and replaced by an implant immediately, "
                        "reducing bone loss and speeding up the timeline. This must be decided with the surgeon in advance."
                    )
                }
            },
            "Warranty & Guarantee": {
                "questions": {
                    "How do you handle warranty on clinical work?": (
                        "We do not offer a warranty on professional cleaning, as new tartar can form within days "
                        "due to inadequate home care. For fillings and restorations, our warranty is 1.5 years. "
                        "For prostheses, crowns, and ceramic veneers, it is 2.5 years.\n\n"
                        "We always strive to assist patients even beyond these periods. If an implant and crown "
                        "were both placed in our clinic, we cover them under warranty. If the implant is placed "
                        "elsewhere and we only do the crown, we guarantee the crown but not the implant."
                    )
                }
            },
            "Important Note on Pricing & Accuracy": {
                "questions": {
                    "What if the bot is unsure about certain prices or procedures?": (
                        "If the bot does not have the exact information, it should inform the patient that it will clarify details "
                        "with the administrator and then follow up. It should never invent an answer."
                    )
                }
            },
        }

    }
}
