# PocketTA submission demo runbook

## Before recording

- Connect power, close memory-heavy applications, disable notifications, and start LM Studio, FastAPI, and Vite.
- Confirm readiness is green and record the exact Whisper and LM Studio versions.
- Open browser developer tools and filter for requests outside `localhost`/`127.0.0.1`.
- Prepare a consented 60–90 second live clip and the completed 10-minute result as a labelled longer example.
- Run the tests/build and one connected benchmark pass.

## Three-minute flow

1. Explain why classroom voices and course material should not require cloud upload.
2. Show local components and disable Wi-Fi visibly.
3. Upload the short clip and show real processing stages.
4. Open the completed longer result; show uncertainty, quiz behavior, and an evidence click.
5. Export Markdown and show metadata, warnings, evidence anchors, and transcript.
6. Delete a disposable lecture and confirm it disappears.
7. Show measured timings and the repository. Never present the prepared result as the live upload.

## Release gate

- [ ] Backend tests, frontend tests, and production build pass.
- [ ] Short and 10-minute samples complete twice with Wi-Fi disabled.
- [ ] Browser Network shows no non-loopback application requests.
- [ ] Export and evidence anchors work.
- [ ] Deletion removes the lecture and later API access returns 404.
- [ ] Restart preserves completed results.
- [ ] Report machine, model versions, timings, counts, and offline status.
- [ ] No private media, weights, `.env`, database, or benchmark output is staged.
- [ ] Backup video and prepared results are honestly labelled.
- [ ] Repository/submission links work signed out.
