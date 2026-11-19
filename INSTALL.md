# Installation

1. Run `./setup.sh` from the project directory.
2. Run `npm start`.
3. Open http://127.0.0.1:8501.
4. If Messages access is denied, enable Full Disk Access for the app launching the server and restart it.
5. To display names, open Contact names in the sidebar, click Allow Contacts, and approve macOS's dialog. Retry name lookup after any permission change.

Development: `npm run dev` starts both the API and Vite. Production-style local use: `npm run build` then `npm start`.

Stop with Ctrl+C. Startup does not register a background service or a login item. All Messages and Contacts operations are reads.
