Yes — I think Sahayak AI needs a RAG system combined with controlled internet access. This is especially important because financial information changes frequently: loan terms, interest rates, eligibility requirements, fees, KYC rules, insurance exclusions, and terms & conditions.

But I wouldn't build a simple chatbot that searches the entire internet and answers whatever it finds. For a financial assistant, we need a trusted, source-grounded knowledge system.

# 1. What exactly should we build?

Sahayak AI Mobile App

User asks: “Explain this loan's terms and conditions.”

AI Orchestration Layer (FastAPI)

Intent detection · Safety checks · Query routing

RAG Knowledge Base

Verified documents, policies, FAQs, T&C

Web Research

Official websites, latest updates, source discovery

Trust & Verification Layer

Source validation · Dates · Conflicts · Citations · Confidence

Grounded AI Response

Simple explanation + sources + effective dates + disclaimers

The two knowledge sources serve different purposes:

- RAG: What we already know from collected, verified documents.
- Internet search: What we need to discover, verify, or update right now.

# 2. Research: technologies worth considering

Here are the tools and resources I recommend evaluating for Sahayak AI.

[How Retrieval-Augmented Generation (RAG) Solves the Limitations of LLMs | by Vinod Rane | Medium](https://images.openai.com/static-rsc-4/nJy9CkmGLNTbezenhKafGMMcMGfG8jXh6Cxxmf0q7m6v_DZFd3Fftl2RDbGRd9Gf1UPV85UUnIuKEaA2qzcRI_qrQVORnjloTQ3QSHyHtpx27YpyuV5F-OSPp8Bt2sjelJfB2hi_l_CPbIdIdeizLr3Q6tA_NcUz56kz_KcyxA8?purpose=inline)

RAG — Retrieval-Augmented Generation

The core knowledge system. Retrieves relevant passages from official documents before the AI generates an answer.

[Official retrieval documentation](https://developers.openai.com/api/docs/guides/retrieval?utm_source=chatgpt.com)

[File search | OpenAI API](https://images.openai.com/static-rsc-4/z7EzwWjB50fwAtyy46VzeU6wVZkQK-F4puWm0nXTSiosEQQSo8GPbIPTvnG44kfK55bKbTDZ0r7N7ZsWImY_HGEW99VPlwTBEthc2yb9OIOIjI70L3gizQ-8GHjs2tSGDnjQf-TLYQYjiLr_IRsYfU_xFm-WpsFdOzgrZpGWu5A?purpose=inline)

OpenAI File Search

Managed retrieval for uploaded PDFs, policies, FAQs and other documents. Supports vector stores and semantic search.

[File Search documentation](https://developers.openai.com/api/docs/guides/tools-file-search?utm_source=chatgpt.com)

[How to Use Firecrawl - Getting Started Guide (2026) | Delv](https://images.openai.com/static-rsc-4/1fdA67pagYyD8njv-o-MH04umewEd87DDiYVdVQuCAy2k_1Qg2AxNj5ifeJ5Z-10gbzGuLHvllHLQx5UAd_l0J-jktz3lj4uyOEYbTDBb9UG7d-sUd9A8LoyKxUz6vjZF4N3aExBijerFH9mV_zWvwdmkZmgOPNRISW5ASoex4s?purpose=inline)

Firecrawl

Useful for crawling official websites, extracting structured information and converting web pages into AI-ready content.

[Official documentation](https://docs.firecrawl.dev/?utm_source=chatgpt.com)[GitHub repository](https://github.com/firecrawl/firecrawl?utm_source=chatgpt.com)

[Crawl4AI: Easy Website Scraping for LLM Data | Siddharth Trivedi posted on the topic | LinkedIn](https://images.openai.com/static-rsc-4/0P1PxtYd06aPhEdQbSDHXuloOD1fpqI8OT7ZLyVp7XxkLAE_qx8MO1oImy8b8VvSKnXssMNXAhje_ltBxN62GswJUl_iucYJSoL__c444F23CEsCA92pzu2tZq_xB6MR9qDAas0O-vcwvP_G91dqu5JDqWkSFsNMH5_dX2V6NXI?purpose=inline)

Crawl4AI

Open-source alternative for self-hosted web crawling and scraping. Interesting for your low-cost approach.

[Documentation](https://docs.crawl4ai.com/?utm_source=chatgpt.com)[GitHub repository](https://github.com/unclecode/crawl4ai?utm_source=chatgpt.com)

[Building a RAG Pipeline with Claude API and Supabase - DEV Community](https://images.openai.com/static-rsc-4/fKjjilPjniaoMmWBYoTBPoqE9JoQqOuHKZyaD9htKYCcmnHJpTlhrwe3MZZ3nzV0SpYppjtb0TMpEWURmgQiE9rCwkAo-RJ4TZbOSepfOvG0jfdSjRkt3PUN4zOAxQK1DNswmOIuwaT2k_V_ZFhJ5NpSiHZX-wNYSfmHYOQpDaU?purpose=inline)

Supabase + pgvector

Store document embeddings alongside structured metadata in PostgreSQL. This integrates naturally with our existing backend recommendation.

[Supabase AI documentation](https://supabase.com/docs/guides/ai?utm_source=chatgpt.com)[pgvector guide](https://supabase.com/docs/guides/database/extensions/pgvector?utm_source=chatgpt.com)

## 3. Financial knowledge sources we should collect

For an India-focused app, we should prioritize official and authoritative sources rather than random financial blogs.

| Source                    | Information to collect                                            | Link                                                                                     |
| ------------------------- | ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| RBI                       | Digital lending rules, borrower rights, KFS, grievance mechanisms | [RBI official website](https://www.rbi.org.in/?utm_source=chatgpt.com)                   |
| RBI Sachet                | Financial consumer awareness and complaint-related resources      | [RBI Sachet](https://sachet.rbi.org.in/?utm_source=chatgpt.com)                          |
| RBI Financial Education   | Financial literacy, responsible borrowing, consumer education     | [Financial education](https://www.rbi.org.in/financialeducation/?utm_source=chatgpt.com) |
| IRDAI                     | Insurance regulations, policyholder protection, insurance FAQs    | [IRDAI official website](https://irdai.gov.in/?utm_source=chatgpt.com)                   |
| NPCI                      | UPI and payment system information, product FAQs                  | [NPCI official website](https://www.npci.org.in/?utm_source=chatgpt.com)                 |
| Official lender websites  | Actual product terms, fees, eligibility, interest rates, T&C      | Individual provider websites                                                             |
| Official insurer websites | Policy documents, exclusions, premiums, claim processes           | Individual insurer websites                                                              |

Useful RBI starting point: [RBI Digital Lending Directions](https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12554\&utm_source=chatgpt.com).

Important: A regulator's general rules and an individual lender's product terms are different sources. We must preserve both and never merge them into a single supposedly universal policy.

# 4. How should the RAG pipeline work?

\#chatgpt-mermaid-\_r_21m\_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica,Apple Color Emoji,Arial,sans-serif,Segoe UI Emoji,Segoe UI Symbol;font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-\_r_21m\_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_21m\_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_21m\_ .error-icon{fill:rgb(48, 48, 48);}#chatgpt-mermaid-\_r_21m\_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_21m\_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-\_r_21m\_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-\_r_21m\_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-\_r_21m\_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-\_r_21m\_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-\_r_21m\_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-\_r_21m\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_21m\_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_21m\_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica,Apple Color Emoji,Arial,sans-serif,Segoe UI Emoji,Segoe UI Symbol;font-size:16px;}#chatgpt-mermaid-\_r_21m\_ p{margin:0;}#chatgpt-mermaid-\_r_21m\_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica,Apple Color Emoji,Arial,sans-serif,Segoe UI Emoji,Segoe UI Symbol;color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_21m\_ .cluster-label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_21m\_ .cluster-label span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_21m\_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-\_r_21m\_ .label text,#chatgpt-mermaid-\_r_21m\_ span{fill:rgb(237, 237, 237);color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_21m\_ .node rect,#chatgpt-mermaid-\_r_21m\_ .node circle,#chatgpt-mermaid-\_r_21m\_ .node ellipse,#chatgpt-mermaid-\_r_21m\_ .node polygon,#chatgpt-mermaid-\_r_21m\_ .node path{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-\_r_21m\_ .rough-node .label text,#chatgpt-mermaid-\_r_21m\_ .node .label text,#chatgpt-mermaid-\_r_21m\_ .image-shape .label,#chatgpt-mermaid-\_r_21m\_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-\_r_21m\_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-\_r_21m\_ .rough-node .label,#chatgpt-mermaid-\_r_21m\_ .node .label,#chatgpt-mermaid-\_r_21m\_ .image-shape .label,#chatgpt-mermaid-\_r_21m\_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-\_r_21m\_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-\_r_21m\_ .root .anchor path{fill:rgb(175, 175, 175)!important;stroke-width:0;stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_21m\_ .arrowheadPath{fill:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_21m\_ .edgePath .path{stroke:rgb(175, 175, 175);stroke-width:1px;}#chatgpt-mermaid-\_r_21m\_ .flowchart-link{stroke:rgb(175, 175, 175);fill:none;}#chatgpt-mermaid-\_r_21m\_ .edgeLabel{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_21m\_ .edgeLabel p{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_21m\_ .edgeLabel rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_21m\_ .labelBkg{background-color:rgba(0, 0, 0, 0.5);}#chatgpt-mermaid-\_r_21m\_ .cluster rect{fill:rgb(48, 48, 48);stroke:rgba(255, 255, 255, 0.15);stroke-width:1px;}#chatgpt-mermaid-\_r_21m\_ .cluster text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_21m\_ .cluster span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_21m\_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica,Apple Color Emoji,Arial,sans-serif,Segoe UI Emoji,Segoe UI Symbol;font-size:12px;background:rgb(48, 48, 48);border:1px solid rgba(255, 255, 255, 0.15);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-\_r_21m\_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_21m\_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-\_r_21m\_ .icon-shape,#chatgpt-mermaid-\_r_21m\_ .image-shape{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_21m\_ .icon-shape p,#chatgpt-mermaid-\_r_21m\_ .image-shape p{background-color:rgb(0, 0, 0);padding:2px;}#chatgpt-mermaid-\_r_21m\_ .icon-shape .label rect,#chatgpt-mermaid-\_r_21m\_ .image-shape .label rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_21m\_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-\_r_21m\_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-\_r_21m\_ .node .neo-node{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-\_r_21m\_ [data-look="neo"].node rect,#chatgpt-mermaid-\_r_21m\_ [data-look="neo"].cluster rect,#chatgpt-mermaid-\_r_21m\_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-\_r_21m\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_21m\_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-\_r_21m\_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-\_r_21m\_-gradient);stroke-width:1px;}#chatgpt-mermaid-\_r_21m\_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_21m\_ [data-look="neo"].node .neo-line path{stroke:rgb(31, 78, 148);filter:none;}#chatgpt-mermaid-\_r_21m\_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-\_r_21m\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_21m\_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-\_r_21m\_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-\_r_21m\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_21m\_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-\_r_21m\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_21m\_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_21m\_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_21m\_ .node tspan[font-weight="normal"],#chatgpt-mermaid-\_r_21m\_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-\_r_21m\_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-width:1px;}#chatgpt-mermaid-\_r_21m\_ .node rect,#chatgpt-mermaid-\_r_21m\_ .node circle,#chatgpt-mermaid-\_r_21m\_ .node ellipse,#chatgpt-mermaid-\_r_21m\_ .node polygon,#chatgpt-mermaid-\_r_21m\_ .node path{fill:rgb(0, 40, 77);stroke:rgba(255, 255, 255, 0.1);stroke-width:1px;}#chatgpt-mermaid-\_r_21m\_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-\_r_21m\_ .mermaid-decision .label-container{fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-dasharray:2,2;}#chatgpt-mermaid-\_r_21m\_ .edgePaths .flowchart-link{stroke:rgb(175, 175, 175);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-\_r_21m\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_21m\_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica,Apple Color Emoji,Arial,sans-serif,Segoe UI Emoji,Segoe UI Symbol;}Official website / PDF / FAQCrawler or document ingestionExtract text and metadataClean, deduplicate, versionSplit into meaningful chunksGenerate embeddingsStore in Supabase pgvectorUser questionIntent detectionSearch relevant chunksRank and validate sourcesLLM generates groundedanswerCitations + date + caveats

### Metadata to store with every document

This is particularly important for financial knowledge.

| Field                | Example                       |
| -------------------- | ----------------------------- |
| `source_name`        | RBI                           |
| `source_url`         | Official document URL         |
| `document_type`      | Circular / FAQ / T&C          |
| `financial_category` | Personal loan                 |
| `provider_name`      | ABC Finance                   |
| `jurisdiction`       | India                         |
| `published_at`       | Publication date              |
| `effective_from`     | Effective date                |
| `last_verified_at`   | Last verification             |
| `version`            | Version number                |
| `content_hash`       | SHA-256 hash                  |
| `status`             | Active / superseded / expired |

This lets Sahayak AI answer questions like:

> "According to this lender's terms effective from September 2026, the processing fee is X. Please verify the latest terms before applying."

If a document is outdated, the system should flag it instead of silently presenting it as current.

# 5. Should we give the AI unrestricted internet access?

No. Give it controlled web-search and retrieval tools.

| User query                                           | Preferred source                                     |
| ---------------------------------------------------- | ---------------------------------------------------- |
| "Explain this uploaded agreement."                   | Document-specific RAG                                |
| "What is RBI's rule on digital lending?"             | Verified regulatory RAG + official source check      |
| "What is the latest interest rate from this lender?" | Live official web search                             |
| "Compare these three loan offers."                   | Structured offer database + deterministic comparison |
| "What does this insurance policy exclude?"           | Exact policy document RAG                            |
| "What is the current government scheme?"             | Official source search + freshness validation        |

The model should decide which tool is relevant, but our backend should enforce what tools are allowed and what sources are trusted.

OpenAI also documents how Web Search can provide current information while File Search retrieves from your own knowledge base: [Current information and API search tools](https://help.openai.com/en/articles/6639781-do-the-openai-api-models-have-knowledge-of-current-events?utm_source=chatgpt.com).

# 6. My recommended approach for your MVP

| Component           | Recommendation                                   |
| ------------------- | ------------------------------------------------ |
| Document ingestion  | Crawl4AI or Firecrawl                            |
| Initial sources     | RBI, official lender websites, FAQs, T&C         |
| Document storage    | Supabase Storage                                 |
| Structured metadata | Supabase PostgreSQL                              |
| Vector search       | pgvector                                         |
| Retrieval           | Hybrid keyword + semantic search                 |
| Reranking           | Optional second-stage relevance ranking          |
| AI orchestration    | FastAPI                                          |
| LLM                 | Pluggable OpenRouter / other provider            |
| Web search          | Search API behind FastAPI                        |
| Response format     | Answer + citations + effective date + confidence |

### Three separate knowledge collections

I would actually build three logical collections, even if they use the same database:

1. Regulatory Knowledge — RBI, IRDAI, NPCI and official regulations.
2. Provider Knowledge — Bank/NBFC/insurer-specific products, fees, eligibility, terms and conditions.
3. User Knowledge — User-uploaded documents, application information and personal financial context.

These must have different access permissions. A user's private documents must never accidentally enter the shared knowledge base.

## 7. Final engineering decision

For Sahayak AI, I recommend building a hybrid RAG + web search + structured financial data system.

RAG alone is not enough because the information can become outdated. Internet access alone is not enough because the model can retrieve unreliable or conflicting sources.

The combination gives us:

- Reliable explanations from verified documents.
- Fresh information from official websites.
- Source citations for users.
- Version and effective-date tracking.
- Clear handling of contradictory information.
- Better transparency and trust.

Next step: We should define and implement the `Knowledge Ingestion & Retrieval` module as its own M0/M1 engineering specification, including database schema, crawler architecture, chunking strategy, retrieval algorithm, API endpoints, source verification and test cases.