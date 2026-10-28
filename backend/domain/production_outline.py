"""Conservative, local-only production outlines from a human editorial review.

The output is an editable *structure*, not a fact-checked script. It never
invents historical facts, Quran quotations, hadith texts, citations, copyright
licenses or guaranteed production costs. No YouTube/LLM calls or persistence.
"""
from domain import editorial_readiness as ER

WORKFLOWS = {
    "kayip": {
        "workingFormat": "historical-documentary",
        "canvas": {"width": 1920, "height": 1080, "aspectRatio": "16:9",
                   "fps": 30, "targetSeconds": 420},
        "steps": [
            ("hook", 0, 20, "Open with a documented question, never an unverified claim.",
             "Introduce your own research question; do not copy the reference title.",
             "document-detail", "On-screen document needs independent provenance."),
            ("context", 20, 90, "Establish the historical period and setting.",
             "Write context only after checking primary/academic references.",
             "animated-map", "Map boundaries and dates need verification."),
            ("evidence", 90, 210, "Explain what the primary sources actually support.",
             "Narrate the verified evidence and identify unresolved points.",
             "archive-document", "Document rights and image reuse must be checked."),
            ("comparison", 210, 310, "Contrast interpretations, without inventing a debate.",
             "Clearly distinguish direct evidence from your own interpretation.",
             "timeline-comparison", "Every date, image and citation must be reviewed."),
            ("assessment", 310, 385, "Discuss limitations and competing explanations.",
             "Explain where sources are silent or disagree.",
             "minimal-explainer", "Do not fabricate people, quotes or archival media."),
            ("closing", 385, 420, "Conclude with what is known and still unknown.",
             "Summarize only checked points and invite further research.",
             "source-list", "Link the actual consulted sources before publishing."),
        ],
        "sourceCategories": ["archive", "museum", "academic", "official"],
        "visualStrategy": "Use appropriately licensed archive material first; Remotion for maps, labels and timelines.",
    },
    "islam": {
        "workingFormat": "islamic-educational-short",
        "canvas": {"width": 1080, "height": 1920, "aspectRatio": "9:16",
                   "fps": 30, "targetSeconds": 60},
        "steps": [
            ("hook", 0, 4, "Introduce a concise question, without a sensational religious claim.",
             "Ask one clear original question suited to a short video.",
             "typography-hook", "Avoid attributing unsourced quotations."),
            ("context", 4, 15, "State what the topic is about.",
             "Define the topic using a verified source, not assumed facts.",
             "subtle-context-motion", "Do not use fabricated sacred texts or imagery."),
            ("evidence", 15, 38, "Present one confirmed verse, hadith or scholarly explanation.",
             "Write exact wording only after reference and interpretation review.",
             "source-text-card", "Verify citation, wording, translation and permitted use."),
            ("lesson", 38, 53, "Provide a carefully qualified takeaway.",
             "Separate source wording from your own explanation.",
             "animated-explainer", "Avoid misleading reenactments and doctrinal certainty."),
            ("closing", 53, 60, "Close briefly with citation context.",
             "Finish without fabricated promises or unsupported rulings.",
             "source-end-card", "Show the source only after independent review."),
        ],
        "sourceCategories": ["quran", "hadith", "scholarly"],
        "visualStrategy": "Use clear caption animation and licensed illustrations; no invented sacred quotations.",
    },
}


def build(payload):
    """Build a bounded plan using the *same* validation as editorial readiness."""
    review = ER.evaluate(payload)
    profile = review["profile"]
    template = WORKFLOWS[profile]
    angle = payload["angle"].strip()
    # The user's own text is marked as an unverified working angle. Reuse is
    # limited to the 1,200 characters already checked by ER.evaluate.
    scenes = [
        {"id": key, "startSeconds": start, "endSeconds": end,
         "purpose": purpose, "narrationInstruction": narration,
         "visualTreatment": treatment, "sourceAndRightsCheck": safeguard,
         "scriptText": None, "assetsAttached": False, "claimsVerified": False}
        for key, start, end, purpose, narration, treatment, safeguard
        in template["steps"]
    ]
    return {
        "profile": profile,
        "workingFormat": template["workingFormat"],
        "workingAngle": angle,
        "angleVerification": "user-supplied-not-fact-checked",
        "format": template["canvas"],
        "scenes": scenes,
        "sourceCategoriesToReview": template["sourceCategories"],
        "submittedSourceCount": review["submittedSources"],
        "reviewedSourceDomainCount": review["uniqueReviewedSourceDomains"],
        "sourceLinksVerified": False,
        "researchBlockers": review["blockers"],
        "researchStatus": review["status"],
        "planStatus": ("outline-for-human-review" if not review["blockers"]
                       else "blocked-provisional-outline"),
        "productionEffort": {
            "userEstimate": review["effortEstimate"],
            "monetaryCostKnown": False,
            "costEstimate": None,
        },
        "voiceover": {
            "method": "creator-recorded-external-microphone",
            "language": "tr",
            "workflow": [
                "Record your own voice in a quiet, untreated-as-possible room.",
                "Save a lossless WAV master; check levels and clipping.",
                "Clean noise, remove mistakes and normalize intelligibility.",
                "Sync scene durations to the approved voice track before rendering.",
            ],
            "recorded": False,
            "durationVerified": False,
        },
        "visuals": {
            "strategy": template["visualStrategy"],
            "animationTool": "Remotion",
            "assetLicensesVerified": False,
            "sourceProvenanceVerified": False,
            "rendered": False,
        },
        "checklist": [
            {"id": "claims", "done": False, "why": "Independently verify exact historical or religious statements."},
            {"id": "sources", "done": False, "why": "Review actual source documents and citations."},
            {"id": "rights", "done": False, "why": "Review every image/video/audio license and permission."},
            {"id": "voice", "done": False, "why": "Record and listen to the creator's real narration."},
            {"id": "timing", "done": False, "why": "Sync editable scene lengths to measured narration."},
            {"id": "originality", "done": False, "why": "Ensure new narrative does not copy competitors."},
            {"id": "final-review", "done": False, "why": "Human editorial review before publication."},
        ],
        "autoGeneratedScript": False,
        "publicationApproved": False,
        "youtubeQuotaUsed": 0,
        "llmUsed": False,
        "databaseWritten": False,
        "note": ("Provisional structure only. Sources, facts, rights, timing, script "
                 "and finished scenes have NOT been externally verified."),
    }
