---
name: create-adr
description: "Use when a proposal, design, or implementation introduces an architectural decision that is not already documented in docs/adr/. Create the ADR before continuing."
---

# Create an ADR

Use this skill when a change introduces a decision that affects the architecture, boundaries, technologies, data, deployment, security, or long-term structure of the project.

## Procedure

1. Inspect `docs/adr/` and identify whether the decision is already documented.
2. If an existing ADR covers the decision, reference it instead of creating a duplicate.
3. If no ADR covers it, create the next sequential file using:

   ```text
   docs/adr/<number>-<short-kebab-case-title>.md
   ```

4. Write the ADR in Spanish with this structure:

   ```markdown
   # ADR-<number>: <título>

   - Estado: Propuesto
   - Fecha: <YYYY-MM-DD>

   ## Contexto

   <problema o necesidad que requiere una decisión>

   ## Decisión

   <decisión adoptada>

   ## Consecuencias

   ### Positivas

   - <consecuencia>

   ### Negativas

   - <consecuencia o trade-off>

   ## Alternativas consideradas

   - <alternativa descartada y motivo>
   ```

5. Link the ADR from the related OpenSpec proposal or design.
6. Do not invent a technology or architecture decision. If the team has not decided yet, create the ADR with `Estado: Propuesto` and leave the decision pending for review.
7. Verify that the ADR number is unique and that the file is included in the change.
