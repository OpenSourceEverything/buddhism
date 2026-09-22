# Audit of OpenSourceEverything/buddhism and Legally Reusable Canon Sources

## Executive conclusion

The repository is presently a **partial Sutta corpus, not a complete Tipitaka**. Its
own README identifies the current extracted-text ledger as
`theravada/tipitaka/sutta/candana-bhikkhu-text-ledger.tsv`, and says the initial
Mind Released ingestion produced 195 usable PDF/text sources. Its detailed comparison
report counts only **188 canonical/source IDs with text**, while much of the apparent
coverage in the repo's reports is actually YouTube metadata rather than committed
canonical text. fileciteturn16file0L2-L2
fileciteturn19file0L2-L2

More importantly, the repository's own coverage document expressly warns that it is
a **coverage and feasibility map, not a permission grant**. I found no permissive
license grant for the underlying Candana Bhikkhu/Mind Released translations in the
materials reviewed. Consequently, their presence in the repository should not be
treated as evidence that they may be commercially redistributed, modified, or
mirrored. fileciteturn17file0L2-L2

The cleanest solution is unusually simple:

**Use SuttaCentral's `bilara-data` published branch as the single primary upstream
for the Pali baseline.** Its Pali tree contains all three baskets -- Sutta, Vinaya,
and Abhidhamma -- and its Abhidhamma directory contains all seven canonical books.
SuttaCentral explicitly says its own material is dedicated to the public domain
under **CC0 1.0 Universal**, permits copying, alteration, redistribution, and other
uses, and identifies the original-language Buddhist texts as public-domain
material. fileciteturn22file0L2-L2
fileciteturn23file0L2-L2
fileciteturn21file0L2-L2

That one upstream can therefore close, with the fewest moving parts:

- the complete Pali Canon baseline;
- the entire seven-book Pali Abhidhamma Pitaka;
- essentially all Pali Sutta gaps in the existing repository; and
- the entire Pali Vinaya.

For English, SuttaCentral also provides a particularly clean Vinaya option:
Bhikkhu Brahmali's **Theravada Collection on Monastic Law**, described in
SuttaCentral's publication metadata as a completed English translation of the Pali
Vinaya Pitaka, with revision ongoing, under CC0. fileciteturn24file0L2-L20
fileciteturn25file0L8-L24
fileciteturn25file1L29-L39

For English Suttas, Bhikkhu Sujato's CC0 material provides the four main Nikayas and
a substantial Khuddaka subset. The published tree contains DN, MN, SN, AN, and KN;
within KN the tree inspected contains Cariyapitaka, Dhammapada, Itivuttaka, Jataka,
Khuddakapatha, Sutta Nipata, Theragatha, Therigatha, and Udana.
fileciteturn26file0L2-L2
fileciteturn27file0L2-L2

I did **not** find a complete English translation of all seven Abhidhamma books that
has comparably clear public-domain, CC0, CC BY, or otherwise commercially permissive
rights. That distinction matters: a complete, legally clean **Pali** Abhidhamma is
available now; a complete, legally clean **English** Abhidhamma should remain an
explicit open gap rather than being silently filled from copyrighted Pali Text
Society, proprietary, or "free distribution only" material.

Confidence in the recommended SuttaCentral Pali import path is **high**. Confidence
in any proposed complete open English Abhidhamma path is **low**, because I found no
source meeting all of the requested coverage and rights criteria.

## Repository baseline and rights state

The repository structure anticipates all three Pitakas, but only the Sutta side is
substantially populated. The Tipitaka directory has `sutta`, `vinaya`, and
`abhidhamma` subdirectories, yet the Abhidhamma directory currently contains only
`.gitkeep`, as does Vinaya. In practical corpus terms, both baskets are empty.
fileciteturn29file0L2-L2
fileciteturn30file0L2-L2
fileciteturn31file0L2-L2

The canonical ledger is useful, but its role should be understood precisely. Its
columns record canonical IDs, extraction status, collection paths, PDF and TXT
paths, sizes, extractor, SHA-256 hash, source URL, label, source page, and errors.
Representative rows are marked `TEXT_EXTRACTED`. In other words, it is primarily an
**ingestion/provenance ledger for material already discovered**, not a normative
list of every text that must exist for a complete Tipitaka.
fileciteturn18file0L2-L2

The companion report makes the incompleteness more visible. It reports 188
text-backed canonical/source IDs against 1,115 YouTube playlist rows. Among the
major Nikayas it records only 9 text-backed DN rows and 33 MN rows; its ordinary SN
playlist has zero text-backed rows, a temporary SN group has 36, and AN has zero.
Sutta Nipata has six book-level text-backed rows, while Theragatha, Therigatha, and
the Dhammapada playlist groups have no text-backed rows in that comparison.
fileciteturn19file0L2-L2

That is why the status file's labels such as `COMPLETE` and `LIKELY COMPLETE` must
not be read as meaning "complete downloadable text exists in the repository." For
example, it calls DN playlist coverage complete at DN 1-34, MN playlist coverage
likely complete, and AN playlist coverage likely complete, while the text-vs-video
report shows only a small fraction of those groups backed by extracted text. The
status file itself distinguishes public playlist coverage from text acquisition.
fileciteturn17file0L2-L2
fileciteturn19file0L2-L2

The repo's Khuddaka status is similarly mixed. Its June 2026 assessment calls
Dhammapada and Udana playlist coverage complete; Itivuttaka partial; Sutta Nipata
and Theragatha likely complete; Therigatha incomplete; Jataka partial; and leaves
Khuddakapatha, Vimanavatthu, Petavatthu, Niddesa, Patisambhidamagga, Apadana,
Buddhavamsa, and Cariyapitaka unassessed. Vinaya and Abhidhamma are also marked not
assessed. fileciteturn17file0L2-L2

There is also an immediate licensing issue with the existing baseline. The repo's
source material is largely associated with Mind Released/Candana Bhikkhu, and its
own documentation says the Mind Released page offered a **selection** of translations
and warns that its coverage analysis is not a rights grant. Therefore the safe
classification for existing Candana-derived PDFs and extracted text is:

**`RIGHTS_UNVERIFIED` -- readable/sourceable, but not established as safe for
commercial redistribution or modification.** fileciteturn17file0L2-L2

That does not mean the translator would object. It means that "available for free"
and "may be redistributed commercially and modified" are legally different
permissions, and the evidence currently recorded in the repo establishes the
former far more clearly than the latter.

## Reusable source audit

The following table separates sources that are useful merely for reading from
sources suitable for the requested open corpus.

| Source | Coverage and language | Format / bulk access | Rights assessment | Maintenance / confidence |
|---|---|---|---|---|
| **SuttaCentral `bilara-data`, Pali root** | Pali Tipitaka tree containing Sutta, Vinaya, and Abhidhamma; Abhidhamma has all seven books: `ds`, `dt`, `kv`, `patthana`, `pp`, `vb`, `ya`. fileciteturn22file0L2-L2 fileciteturn23file0L2-L2 | Segment-oriented JSON in Git; whole repository can be cloned/mirrored; Bilara tooling supports collection exports. | **ACCEPT. CC0 / public-domain treatment.** SuttaCentral says its original material is CC0 and explicitly permits copying, altering and redistributing; it separately describes original Buddhist-language texts as public domain. fileciteturn21file0L2-L2 | Active project; published branch intended for distributable material. **High confidence.** |
| **SuttaCentral, Sujato English Suttas** | English; Bhikkhu Sujato. Published tree has DN, MN, SN, AN and KN. KN inspected contains CP, Dhp, Iti, Ja, Kp, Snp, Thag, Thig and Ud. fileciteturn26file0L2-L2 fileciteturn27file0L2-L2 | Bilara JSON/Git; bulk clone and programmatic conversion possible. | **ACCEPT where publication metadata says CC0.** SuttaCentral requires supported translation projects to carry explicit licensing metadata; its publication data records CC0 licenses. fileciteturn20file0L2-L23 | Actively revised published data. **High confidence for individual CC0 records; do not blanket-license unrelated legacy translations.** |
| **SuttaCentral, Brahmali Vinaya** | English, Bhikkhu Brahmali; "Theravada Collection on Monastic Law", explicitly an English translation of the Pali Vinaya Pitaka; publication marked completed, revision ongoing. fileciteturn24file0L8-L20 fileciteturn25file0L8-L24 | Bilara JSON/Git, collection-level tree. | **ACCEPT. CC0.** Publication metadata records Creative Commons Zero. fileciteturn25file1L29-L39 | Completed but actively revised. **High confidence.** |
| **CRAN `tipitaka` package** | Complete Pali Canon represented as Vinaya, Sutta and Abhidhamma data objects; sourced from the Chaṭṭha Sangayana/VRI textual tradition. | R package data, source tarball, GitHub mirror; convenient machine-readable bulk corpus. | Package metadata declares **CC0**, making it attractive technically. However, its provenance through VRI makes the chain of rights less clean than SuttaCentral's own explicit licensing framework. **Accept only after preserving and reviewing provenance; secondary choice.** | Current 1.0.0-era package in 2026. **Medium confidence on chain of title; high on stated package license.** |
| **Ancient Buddhist Texts** | Pali editions and English translations of many individual works; includes useful Sutta material and some Abhidhamma/Vinaya portions, but it is not the simplest complete three-basket source. | HTML plus downloadable PDF/EPUB/MOBI for many works; primarily work-by-work rather than one canonical API. | Many reviewed works use **CC BY-SA 4.0**, which permits commercial reuse and adaptation with attribution and ShareAlike. **Accept per work after checking that work's notice.** | Long-running scholarly site. **High confidence per explicitly licensed work; not a blanket license assumption.** |
| **VRI / tipitaka.org** | Complete Sixth Council Pali material; separate bulk archives exist for Vinaya, Sutta and Abhidhamma. | Downloadable archives/PDFs and CST software. | **FLAG / DO NOT USE AS PRIMARY IMPORT.** Availability and research use are clear, but I did not find a text-wide grant as explicit as CC0 allowing modification and commercial redistribution. Other VRI assets, such as fonts, carry separate restrictions. | Stable long-standing source. **High textual confidence, low licensing confidence for the requested commercial reuse.** |
| **Pali Text Society** | Important English translations across all three baskets, including several Abhidhamma books and the traditional multi-volume Vinaya. | Books, some digital offerings. | **REJECT for the requested baseline.** PTS's current copyright information places numerous canonical translations under **CC BY-NC**, while retaining commercial rights. NC fails the commercial-use requirement. Its English Patthana publication is also not a complete translation of the entire canonical Patthana. | Active publisher. **High confidence.** |
| **Access to Insight** | Large but incomplete English Sutta collection from multiple translators. | Website; historical whole-site downloads have existed. | **REJECT as a blanket corpus.** Rights are mixed. Some material is CC BY-NC; some uses custom "free distribution only" conditions; a site-level license cannot safely be projected onto every contributed translation. | Legacy/stable resource. **High confidence that per-work auditing is mandatory.** |
| **Dhammatalks.org / Thanissaro Bhikkhu** | Very substantial English Sutta corpus, but not a complete three-basket Tipitaka. | HTML, ebooks and collections. | **REJECT for commercial corpus import.** Modern works commonly use CC BY-NC 4.0; older works may say "for free distribution only." Both fail the requested unrestricted commercial criterion. | Actively maintained. **High confidence.** |
| **PaliVerse** | Broad English Tipitaka-oriented reading platform, including material beyond the four Nikayas. | Web application; systematic bulk copying is restricted by its terms. | **REJECT. Proprietary/personal-use terms.** Its permissions distinguish public-domain Pali source text from copyrighted English translations and other platform content, and do not provide the needed right to freely mirror, modify and commercially redistribute the English corpus. | Active in 2026. **High confidence.** |
| **E-Pitaka** | AI-assisted English translation project built around the Pali canon and other translations. | Web project and open-source technical components. | **FLAG / DO NOT IMPORT TEXT.** Open-source pipeline code is not itself an open-content license for the generated translation corpus. I found no sufficiently clear corpus-wide CC0/CC BY grant establishing commercial redistribution and modification rights. | Work in progress. **Medium-high confidence that a separate content license is required.** |
| **Mind Released / Candana Bhikkhu** | Selected English Pali Sutta translations; source of the repo's existing extraction work. | Individual downloadable PDFs; repo already records source URLs and hashes. fileciteturn18file0L2-L2 | **FLAG: UNCLEAR.** The repo itself expressly says its coverage work is not a permission grant. Do not infer commercial redistribution/modification rights from free downloadability. fileciteturn17file0L2-L2 | Current enough to have been crawled in the repo's 2026 work. **High confidence that explicit permission is still needed.** |

The exact license most useful here is:

`https://creativecommons.org/publicdomain/zero/1.0/`

SuttaCentral's licensing text says material it creates is dedicated to the public
domain through CC0 1.0 Universal. Although it **requests** attribution and adherence
to Buddhist values, it describes those as requests rather than legal obligations.
It also distinguishes third-party "legacy" translations, whose separate rights
notices must still be honored. fileciteturn21file0L2-L2

That distinction is important because one must not reason:

"SuttaCentral is CC0, therefore every translation displayed on SuttaCentral is CC0."

SuttaCentral itself says otherwise: third-party material can retain separately
asserted copyright and licenses. The import pipeline should therefore whitelist
specific CC0 publication records rather than treating the domain as one homogeneous
license pool. fileciteturn21file0L2-L2

One additional complication is worth recording. At least one SuttaCentral publication
record found in the data combines an explicit CC0 declaration with a prose request
not to use the work for AI training. Because CC0 is itself an unconditional public
domain dedication rather than an NC/ND-style license, such prose should not silently
be converted into a new legal restriction; nevertheless, I would flag that record
as an **ethical/request-level conflict** and avoid it where an equally complete
unconflicted source exists. fileciteturn20file1L39-L68

For CC BY-SA material, the relevant standard license is:

`https://creativecommons.org/licenses/by-sa/4.0/`

It permits commercial reuse and modifications, but attribution is mandatory and
adapted material must remain under the compatible ShareAlike terms. It is therefore
legally usable but operationally less convenient than CC0 for a canonical baseline.

By contrast, CC BY-NC material should be excluded from this project if the objective
is a corpus that anyone can mirror or commercially reuse without seeking further
permission. A useful reference URL is:

`https://creativecommons.org/licenses/by-nc/4.0/`

## Gap matrix against the repository

The matrix below treats **actual text availability and rights**, rather than playlist
coverage, as the meaningful baseline.

| Canonical collection | Repository state | Legally safe gap | Smallest safe fill |
|---|---|---|---|
| **Tipitaka overall** | No complete canonical corpus. Current work is concentrated on selected Sutta PDFs/texts; Vinaya and Abhidhamma are empty. fileciteturn16file0L2-L2 fileciteturn30file0L2-L2 fileciteturn31file0L2-L2 | Nearly the whole canon when measured as a rights-cleared baseline. | SuttaCentral Pali `root/pli/ms/{sutta,vinaya,abhidhamma}`, CC0/public-domain framework. fileciteturn22file0L2-L2 |
| **Digha Nikaya** | Playlist status says DN 1-34 complete, but comparison report has only 9 text-backed DN rows. fileciteturn17file0L2-L2 fileciteturn19file0L2-L2 | Most DN lacks a rights-cleared canonical text baseline in the repo. | SuttaCentral full Pali DN; optionally Sujato English DN, CC0. fileciteturn26file0L2-L2 |
| **Majjhima Nikaya** | Playlist likely complete, but only 33 text-backed rows in the report; canonical target noted as MN 1-152. fileciteturn17file0L2-L2 fileciteturn19file0L2-L2 | Large text gap. | SuttaCentral full Pali MN; optionally Sujato English, CC0. fileciteturn26file0L2-L2 |
| **Samyutta Nikaya** | Explicitly partial; report shows zero text-backed rows in the primary playlist group and 36 in the temporary group. fileciteturn17file0L2-L2 fileciteturn19file0L2-L2 | Very large text gap across 56 samyuttas. | SuttaCentral full Pali SN; optionally Sujato English, CC0. fileciteturn26file0L2-L2 |
| **Anguttara Nikaya** | Playlist called likely complete, but comparison report has **0 text-backed rows** for its 185 playlist rows. fileciteturn17file0L2-L2 fileciteturn19file0L2-L2 | Essentially complete text baseline missing. | SuttaCentral full Pali AN; optionally Sujato English, CC0. fileciteturn26file0L2-L2 |
| **Khuddakapatha** | Not assessed. fileciteturn17file0L2-L2 | Treat as absent/unverified. | SuttaCentral Pali; Sujato English `kp` is present in published tree. fileciteturn27file0L2-L2 |
| **Dhammapada** | Playlist coverage considered complete, but report shows zero text-backed Dhammapada playlist rows. fileciteturn17file0L2-L2 fileciteturn19file0L2-L2 | Rights-cleared standardized text still needed. | SuttaCentral Pali plus Sujato English `dhp`, CC0. fileciteturn27file0L2-L2 |
| **Udana** | Playlist considered complete; combined Udana/Itivuttaka group has only 2 text-backed rows in report. fileciteturn17file0L2-L2 fileciteturn19file0L2-L2 | Most standardized text missing. | SuttaCentral Pali plus Sujato English `ud`, CC0. fileciteturn27file0L2-L2 |
| **Itivuttaka** | Partial; status suggests Iti 1-112 except possible gap at 94; combined report is overwhelmingly metadata-only. fileciteturn17file0L2-L2 fileciteturn19file0L2-L2 | Incomplete. | SuttaCentral Pali plus Sujato English `iti`, CC0. fileciteturn27file0L2-L2 |
| **Sutta Nipata** | Likely complete in six book-level Mind Released files; report shows all six rows text-backed. fileciteturn17file0L2-L2 fileciteturn19file0L2-L2 | Coverage may be good, but redistribution rights of existing translation are unclear. | Replace or supplement with SuttaCentral Pali and Sujato English `snp`, CC0. fileciteturn27file0L2-L2 |
| **Vimanavatthu** | Not assessed. fileciteturn17file0L2-L2 | Missing. | SuttaCentral Pali. Do not claim Sujato English coverage from the tree inspected. |
| **Petavatthu** | Not assessed. fileciteturn17file0L2-L2 | Missing. | SuttaCentral Pali. |
| **Theragatha** | Playlist likely complete; report has zero text-backed rows. fileciteturn17file0L2-L2 fileciteturn19file0L2-L2 | Text baseline missing. | SuttaCentral Pali plus Sujato English `thag`, CC0. fileciteturn27file0L2-L2 |
| **Therigatha** | Explicitly incomplete; playlist only reached the Book of Five Verses in the repo's audit. fileciteturn17file0L2-L2 | Significant gap. | SuttaCentral Pali plus Sujato English `thig`, CC0. fileciteturn27file0L2-L2 |
| **Jataka** | Partial. fileciteturn17file0L2-L2 | Canonical text incomplete; distinguish canonical verses from later commentary/stories. | SuttaCentral Pali canonical material; Sujato tree contains `ja`, but do not equate this automatically with the complete later Jataka commentary. fileciteturn27file0L2-L2 |
| **Niddesa** | Not assessed. fileciteturn17file0L2-L2 | Missing. | SuttaCentral Pali. |
| **Patisambhidamagga** | Not assessed. fileciteturn17file0L2-L2 | Missing. | SuttaCentral Pali. |
| **Apadana** | Not assessed. fileciteturn17file0L2-L2 | Missing. | SuttaCentral Pali. |
| **Buddhavamsa** | Not assessed. fileciteturn17file0L2-L2 | Missing. | SuttaCentral Pali. |
| **Cariyapitaka** | Not assessed. fileciteturn17file0L2-L2 | Missing in current baseline. | SuttaCentral Pali plus Sujato English `cp`, CC0. fileciteturn27file0L2-L2 |
| **Vinaya Pitaka** | Directory contains only `.gitkeep`; status previously not assessed. fileciteturn31file0L2-L2 fileciteturn17file0L2-L2 | **Entire basket missing.** | SuttaCentral Pali Vinaya plus, if English desired, Brahmali's complete CC0 translation. fileciteturn22file0L2-L2 fileciteturn25file0L8-L24 |
| **Dhammasangani** | Abhidhamma directory empty. fileciteturn30file0L2-L2 | Entire book missing. | SuttaCentral Pali `ds`, CC0/public-domain framework. fileciteturn23file0L2-L2 |
| **Vibhanga** | Empty. fileciteturn30file0L2-L2 | Entire book missing. | SuttaCentral Pali `vb`. fileciteturn23file0L2-L2 |
| **Dhatukatha** | Empty. fileciteturn30file0L2-L2 | Entire book missing. | SuttaCentral Pali `dt`. fileciteturn23file0L2-L2 |
| **Puggalapannatti** | Empty. fileciteturn30file0L2-L2 | Entire book missing. | SuttaCentral Pali `pp`. fileciteturn23file0L2-L2 |
| **Kathavatthu** | Empty. fileciteturn30file0L2-L2 | Entire book missing. | SuttaCentral Pali `kv`. fileciteturn23file0L2-L2 |
| **Yamaka** | Empty. fileciteturn30file0L2-L2 | Entire book missing. | SuttaCentral Pali `ya`. fileciteturn23file0L2-L2 |
| **Patthana** | Empty. fileciteturn30file0L2-L2 | Entire book missing. | SuttaCentral Pali `patthana`; importantly, this avoids representing partial English PTS translations as the complete work. fileciteturn23file0L2-L2 |

The canonical boundary of the Khuddaka Nikaya should itself be recorded as metadata
rather than hard-coded as universally fixed. Different Theravada national editions
have historically differed over the status or placement of works such as
Nettipakarana, Petakopadesa, and Milindapanha. The repository already lists these
among collections to consider, so a future canonical ledger should identify the
chosen recension explicitly rather than simply marking the entire Khuddaka
collection "complete." The existing status file already exposes these items
separately, which is a good starting point. fileciteturn17file0L2-L2

## Copyright and licensing boundary

The most important legal distinction in this project is between an **ancient
underlying Pali work** and a **modern expression of that work**.

SuttaCentral's licensing material explicitly describes the original Buddhist texts
in Pali and other ancient languages as public-domain material, while treating
translations created by third parties as a separate copyright category. That is
the right conceptual model for the repository. fileciteturn21file0L2-L2

A modern translator does not acquire copyright in the Buddha's ancient source text
merely by translating it. But the translator can hold copyright in the translator's
own English wording. Likewise, a modern edition can include protectable introductions,
annotations, apparatus, editorial commentary, artwork, typography, or database
structure even where the ancient underlying words themselves are public domain.
Consequently:

**Public-domain Pali does not imply public-domain English.**

And:

**A freely downloadable English translation does not imply a right to modify it,
sell it, mirror it, or incorporate it into another corpus.**

This is why the SuttaCentral CC0 translation records are materially more useful than
"free distribution only" translations. CC0 gives the project a clear downstream
right to reproduce and transform the translated expression itself, whereas a
free-reading or free-distribution statement may be much narrower.

For this repository, I would use the following machine-readable rights classes:

| Class | Import policy |
|---|---|
| `PD` | Accept; preserve provenance and the public-domain basis. |
| `CC0-1.0` | Accept; no legal attribution requirement, but retain provenance and honor reasonable attribution requests. |
| `CC-BY-*` | Accept; generate attribution automatically and retain license/change notices. |
| `CC-BY-SA-*` | Accept only in a clearly separated license domain; derivatives must satisfy ShareAlike. |
| `CC-BY-NC-*` | Reject from commercial/open baseline. |
| `CC-BY-ND-*` | Reject where normalization, correction, segmentation, or other adaptation may be required. |
| `FREE-DISTRIBUTION-ONLY` | Reject from commercially reusable baseline unless the exact grant expressly permits the intended uses. |
| `PERSONAL-USE` | Reject. |
| `PERMISSION-ONLY` | Reject until written permission is archived. |
| `UNCLEAR` | Quarantine; do not publish as rights-cleared. |
| `CONFLICTING` | Quarantine pending a work-specific legal/licensor clarification. |

For CC0 SuttaCentral material, attribution is not presented as a legal condition;
SuttaCentral nevertheless respectfully requests attribution. The repository should
honor that request because it costs essentially nothing and substantially improves
provenance. fileciteturn21file0L2-L2

A good attribution/provenance record would retain, per imported collection:

`source_project`,
`source_repository`,
`source_branch`,
`upstream_commit`,
`source_path`,
`canonical_id`,
`language`,
`translator/editor`,
`license_id`,
`license_url`,
`upstream_rights_statement`,
`retrieved_at`,
`source_sha256`,
`normalized_sha256`,
and `transformation_history`.

That is especially important for a living corpus such as Bilara because the
published translations are revised. Brahmali's Vinaya publication metadata, for
example, explicitly says "Completed, revision is ongoing." Pinning an upstream
commit makes an otherwise moving corpus reproducible. fileciteturn25file0L8-L24

## Recommended minimal import plan

The smallest legally safe plan is **not** to aggregate every promising Buddhist site.
It is to reduce the number of licensors and provenance chains as aggressively as
possible.

### Primary canonical layer

Use only this upstream for the initial canonical Pali corpus:

`https://github.com/suttacentral/bilara-data`

Pin the `published` branch to a specific commit at import time and take only:

`root/pli/ms/sutta`

`root/pli/ms/vinaya`

`root/pli/ms/abhidhamma`

The upstream directory itself confirms that these are the three Pali baskets.
fileciteturn22file0L2-L2

For Abhidhamma, require exactly these seven top-level book identifiers before an
import can be called complete:

`ds`
`vb`
`dt`
`pp`
`kv`
`ya`
`patthana`

All seven are present in the published SuttaCentral Pali tree.
fileciteturn23file0L2-L2

License record:

`CC0-1.0`

License URL:

`https://creativecommons.org/publicdomain/zero/1.0/`

SuttaCentral rights statement in the source corpus:

`https://github.com/suttacentral/bilara-data/blob/published/`
`root/en/site/licensing_root-en-site.json`

SuttaCentral says its own original material is CC0, invites copying, altering and
redistributing it, and identifies original Buddhist texts as public-domain material.
fileciteturn21file0L2-L2

This single-source step gives the repository its first coherent, complete
machine-readable Pali baseline without depending on the licensing of the existing
Candana translations.

### Optional English layer

Add English only as a separate translation layer, never by replacing the canonical
Pali files.

For Suttas, whitelist:

`translation/en/sujato/sutta`

The published tree presently covers DN, MN, SN, AN, and a defined KN subset.
fileciteturn26file0L2-L2
fileciteturn27file0L2-L2

Do **not** mark "English Sutta Pitaka complete" merely because the four main Nikayas
are complete. The inspected Sujato KN directory contains nine collections, not every
Khuddaka work in the Pali canonical baseline. fileciteturn27file0L2-L2

For Vinaya, whitelist:

`translation/en/brahmali/vinaya`

The SuttaCentral metadata identifies this as Bhikkhu Brahmali's English translation
of the Pali Vinaya Pitaka, marks it published and completed with ongoing revision,
and records a CC0 license. fileciteturn24file0L8-L20
fileciteturn25file0L8-L24
fileciteturn25file1L29-L39

For Abhidhamma, import **Pali only** at this stage. Do not manufacture an apparently
complete English collection from a patchwork of old PTS translations, partial
Patthana translations, newer copyrighted works, and unclear web editions. The
legally honest metadata value should be:

`english_complete = false`

until a complete seven-book English set with suitable rights is located or newly
created.

### Treatment of the existing Candana corpus

Do not delete it merely because its rights are unclear. Instead separate **coverage**
from **redistribution clearance**.

Existing ledger rows can remain valuable for source identification, translation
comparison, audio linking, and research. The ledger already preserves source URLs,
PDF/TXT paths, hashes, labels and canonical IDs. fileciteturn18file0L2-L2

But add a rights field and initialize Candana/Mind Released material to something
like:

`license_status = UNCLEAR`

`commercial_redistribution = UNKNOWN`

`modification = UNKNOWN`

`source_permission_evidence = NONE_RECORDED`

That faithfully reflects the repo's own warning that its coverage file is not a
permission grant. fileciteturn17file0L2-L2

Only promote those rows to the open distribution set after either an explicit
standard license is found or the rights holder provides a written grant covering
redistribution, modification, mirroring and commercial use.

### Sources not needed for the minimal plan

Do not import PTS, Access to Insight, Dhammatalks, PaliVerse, E-Pitaka, or VRI text
into the first rights-cleared baseline.

PTS/ATI/Dhammatalks introduce NC, free-distribution, or mixed-license problems.
PaliVerse is useful for reading but does not supply the desired open redistribution
rights. E-Pitaka's open technical implementation does not establish a comparably
clear open license for all generated English translation content. VRI is an
important textual provenance source, but its redistribution grant is less explicit
than the SuttaCentral CC0 route.

Ancient Buddhist Texts is the strongest optional supplementary source among those
alternatives because explicitly CC BY-SA works can be commercially reused and
modified. Nevertheless it should be used only where it fills a real scholarly or
translation gap, with each imported work's exact license and attribution retained.
It is unnecessary for obtaining the complete Pali baseline because SuttaCentral
already closes that gap with simpler licensing.

The resulting architecture would therefore be:

```text
theravada/
  tipitaka/
    pali/
      suttacentral/
        vinaya/
        sutta/
        abhidhamma/

    translations/
      en/
        suttacentral/
          sujato/
            sutta/
          brahmali/
            vinaya/

    legacy-or-rights-unverified/
      candana/
```

The important conceptual separation is between **canonical identity**,
**language/translation**, and **license status**. A translation should never become
the canonical ledger itself; rather, canonical IDs should point to zero or more
licensed textual witnesses.

With that design, the repository can truthfully make three strong claims after a
future import without overstating anything:

**Complete Pali Tipitaka baseline:** yes.

**Complete Pali Abhidhamma Pitaka:** yes, all seven books.

**Complete freely modifiable/commercial English Tipitaka:** no.

That last "no" is not a failure. It is the licensing fact that prevents a corpus
from appearing more open or complete than its evidence supports.
