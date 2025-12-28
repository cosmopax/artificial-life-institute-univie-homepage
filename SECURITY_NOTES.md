# Security Notes

- **Static Site**: No server-side logic or database. Attack surface is minimal.
- **Secrets**: Do not commit passwords or private keys.
- **Deploy**: `deploy.sh` moves old content to `__quarantine__`. Ensure the web server (Apache/Nginx on univie) has correct permissions.
- **Privacy**: No tracking scripts or cookies (except local storage for theme preference).
- **Public Claims**: All research claims must be cited or stated with uncertainty.
