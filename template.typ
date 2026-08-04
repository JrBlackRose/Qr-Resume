// ═══════════════════════════════════════════════════════════════════════════
//  Resume AI — Typst Template
//  Reads structured data from resume_data.json (generated at compile time).
//  Compile with:  typst compile template.typ output.pdf
// ═══════════════════════════════════════════════════════════════════════════

#let data = json("resume_data.json")

// ── Document & Page ──────────────────────────────────────────────────────────
#set document(
  title:  data.contact.name + " — Resume",
  author: data.contact.name,
)

#set page(
  paper:  "us-letter",
  margin: (x: 0.68in, top: 0.58in, bottom: 0.62in),
)

// ── Typography ───────────────────────────────────────────────────────────────
// Font stack: tries Liberation Sans first (common Linux/Win), then Helvetica
// Neue (macOS), then Arial, then falls back to Typst's bundled sans-serif.
#set text(
  font: ("Liberation Sans", "Helvetica Neue", "Arial", "New Computer Modern Sans"),
  size: 10.5pt,
  lang: "en",
  hyphenate: false,
)
#set par(leading: 0.58em, justify: false)

// ── Colour Palette ───────────────────────────────────────────────────────────
#let c-navy    = rgb("#1b2a4a")   // header background, section titles
#let c-steel   = rgb("#2c5f8a")   // company names, institution names
#let c-muted   = rgb("#556070")   // secondary text, dates, locations
#let c-accent  = rgb("#9ab0cc")   // contact line inside dark header
#let c-bullet  = rgb("#3a7abf")   // bullet triangle colour

// ── Helpers ──────────────────────────────────────────────────────────────────

// Bold section header with a full-width rule underneath
#let section(title) = {
  v(0.52em)
  text(
    size: 9.8pt,
    weight: "bold",
    fill: c-navy,
    tracking: 1.4pt,
  )[#upper(title)]
  v(2.5pt)
  line(length: 100%, stroke: (paint: c-navy, thickness: 0.7pt))
  v(0.22em)
}

// A single bullet point with a small coloured triangle marker
#let bullet-row(content) = {
  pad(
    left: 1.05em,
    top: 1.5pt,
    bottom: 0.5pt,
  )[
    #text(fill: c-bullet, size: 9pt)[▸]
    #h(4pt)
    #text(size: 10pt)[#content]
  ]
}

// One work-experience block
#let job-block(job) = {
  // Title row: role | company | location  ────────────────── dates
  grid(
    columns: (1fr, auto),
    column-gutter: 6pt,
    align: (left + horizon, right + horizon),
    // Left cell
    [
      #text(weight: "bold", size: 10.5pt, fill: c-navy)[#job.title]
      #h(5pt)
      #text(size: 10pt, fill: c-steel)[#job.company]
      #if job.location != "" [
        #h(5pt)
        #text(size: 9.2pt, fill: c-muted)[· #job.location]
      ]
    ],
    // Right cell
    text(size: 9pt, fill: c-muted)[#job.start_date – #job.end_date],
  )
  v(0.1em)
  for b in job.bullets {
    bullet-row(b)
  }
  v(0.38em)
}

// One education block
#let edu-block(edu) = {
  grid(
    columns: (1fr, auto),
    column-gutter: 6pt,
    align: (left + horizon, right + horizon),
    [
      #text(weight: "bold", size: 10.5pt, fill: c-navy)[#edu.degree]
      #linebreak()
      #text(size: 10pt, fill: c-steel)[#edu.institution]
      #if edu.location != "" [
        #h(5pt)
        #text(size: 9.2pt, fill: c-muted)[· #edu.location]
      ]
      #if edu.gpa != "" [
        #h(5pt)
        #text(size: 9.2pt, fill: c-muted)[· GPA: #edu.gpa]
      ]
    ],
    text(size: 9pt, fill: c-muted)[#edu.graduation_date],
  )
  v(0.38em)
}


// ═══════════════════════════════════════════════════════════════════════════
//  HEADER
// ═══════════════════════════════════════════════════════════════════════════

// Collect non-empty contact fields into a flat array for the contact line
#let contact-parts = (
  data.contact.email,
  data.contact.phone,
  data.contact.location,
  data.contact.linkedin,
  data.contact.github,
).filter(s => s != "")

#block(
  width:  100%,
  fill:   c-navy,
  inset:  (x: 16pt, y: 14pt),
  radius: 5pt,
)[
  #align(center)[
    // Full name
    #text(size: 24pt, weight: "bold", fill: white)[#data.contact.name]

    #if contact-parts.len() > 0 [
      #v(6pt)
      // Contact details on one line separated by centred dots
      #text(size: 9pt, fill: c-accent)[
        #contact-parts.join("  ·  ")
      ]
    ]
  ]
]

#v(0.52em)


// ═══════════════════════════════════════════════════════════════════════════
//  PROFESSIONAL SUMMARY
// ═══════════════════════════════════════════════════════════════════════════

#if data.summary != "" {
  section("Professional Summary")
  block(width: 100%)[
    #text(size: 10.2pt)[#data.summary]
  ]
  v(0.18em)
}


// ═══════════════════════════════════════════════════════════════════════════
//  PROFESSIONAL EXPERIENCE
// ═══════════════════════════════════════════════════════════════════════════

#if data.experience.len() > 0 {
  section("Professional Experience")
  for job in data.experience {
    job-block(job)
  }
}


// ═══════════════════════════════════════════════════════════════════════════
//  EDUCATION
// ═══════════════════════════════════════════════════════════════════════════

#if data.education.len() > 0 {
  section("Education")
  for edu in data.education {
    edu-block(edu)
  }
}


// ═══════════════════════════════════════════════════════════════════════════
//  SKILLS
// ═══════════════════════════════════════════════════════════════════════════

#let tech-skills = data.skills.technical
#let soft-skills = data.skills.soft

#if tech-skills.len() > 0 or soft-skills.len() > 0 {
  section("Skills")

  if tech-skills.len() > 0 {
    grid(
      columns: (80pt, 1fr),
      column-gutter: 6pt,
      row-gutter:    4pt,
      text(weight: "bold", size: 10pt, fill: c-navy)[Technical:],
      text(size: 10pt)[#tech-skills.join("  ·  ")],
    )
  }

  if soft-skills.len() > 0 {
    v(3pt)
    grid(
      columns: (80pt, 1fr),
      column-gutter: 6pt,
      row-gutter:    4pt,
      text(weight: "bold", size: 10pt, fill: c-navy)[Soft Skills:],
      text(size: 10pt)[#soft-skills.join("  ·  ")],
    )
  }
}
