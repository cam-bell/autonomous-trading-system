# Evaluation Notes

## What To Evaluate

The project should be evaluated as a combination of product surface and systems implementation.

- Can a reviewer understand what each trader is doing quickly?
- Can the system be demoed repeatedly without fragile setup?
- Can multiple traders be compared in a way that surfaces real behavioral differences?
- Does the repo explain enough of the underlying architecture to be credible?

## Functional Checks

- Dashboard loads with seeded replay data when configured
- Summary cards, detail panels, and compare mode render coherent state
- Manual run flow updates logs, holdings, and transactions after execution
- Local paths for database and memory resolve correctly

## Portfolio Checks

- README explains the project without requiring code inspection first
- Architecture and workflow diagrams make the system legible at a glance
- Repo structure and docs suggest deliberate systems design rather than a one-off script

## Future Evaluation Opportunities

- Add real screenshots and a short demo GIF
- Add a small before/after evaluation of seeded replay versus raw-log review
- Add lightweight performance or cost observations once the hosted demo stabilizes
