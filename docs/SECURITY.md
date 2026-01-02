# Security Documentation

## ⚠️ Token Security Warning

This tool uses **Slack session tokens** (xoxc and xoxd), which are user-level credentials extracted from your browser. These tokens have significant security implications that you must understand before use.

### Critical Security Considerations

#### 1. Token Permissions
- **Full User Access**: Session tokens grant the same permissions as your logged-in user account
- **No Scope Limitations**: Unlike bot tokens, session tokens aren't restricted to specific permissions
- **Account Compromise**: If tokens are leaked, attackers can act as you in your workspace

#### 2. Token Expiration
- **Short-Lived**: Session tokens typically expire after a few hours or days
- **No Refresh**: Unlike OAuth tokens, there's no programmatic way to refresh them
- **Manual Renewal**: You must extract new tokens from your browser when they expire
- **Signs of Expiration**:
  - API responses return `invalid_auth` errors
  - HTTP 401 Unauthorized responses
  - Messages fail to post with authentication errors

#### 3. Token Storage
- **NEVER commit tokens to version control**: Always use `.env` files (add to `.gitignore`)
- **NEVER share tokens**: Treat them like passwords
- **NEVER log tokens**: Ensure they don't appear in logs or error messages
- **Use environment variables**: Load from `.env` only, never hardcode

### Best Practices

#### Secure Token Extraction

1. **Open Slack in Browser**: Use Chrome/Firefox (not the desktop app)
2. **Open Developer Tools**: Press `F12` or `Cmd+Option+I` (Mac)
3. **Go to Network Tab**: Filter by "XHR" requests
4. **Trigger an Action**: Send a message or navigate
5. **Find API Request**: Look for requests to `api/` endpoints
6. **Extract Tokens**:
   - Find `xoxc-*` token in request headers or form data
   - Find `xoxd-*` token in cookies under `d=`
7. **Use Immediately**: Don't store long-term; extract fresh tokens when needed

#### Environment File Security

```bash
# .env file should have restrictive permissions
chmod 600 .env

# Verify it's in .gitignore
grep -q "^\.env$" .gitignore || echo ".env" >> .gitignore
```

#### Token Rotation

- **Extract fresh tokens** for each testing session
- **Don't reuse** tokens across multiple days
- **Monitor expiration**: If posts fail, extract new tokens
- **Use test workspaces**: Don't use production workspace tokens for testing

#### Workspace Isolation

- **Create a dedicated test workspace** for this tool
- **Don't use in production workspaces** unless absolutely necessary
- **Use test channels**: Create isolated channels for testing
- **Limit team access**: Minimize who has access to test workspaces

### What NOT to Do

❌ **NEVER** commit `.env` to git  
❌ **NEVER** share tokens in chat, email, or tickets  
❌ **NEVER** use production tokens for development  
❌ **NEVER** hardcode tokens in source code  
❌ **NEVER** use the same tokens across multiple machines  
❌ **NEVER** store tokens in plaintext outside `.env`  
❌ **NEVER** bypass `.gitignore` for `.env` files

### Emergency Response

If you accidentally expose tokens:

1. **Revoke Access Immediately**:
   - Log out of Slack in the browser where tokens were extracted
   - Clear browser cookies for Slack
   - Log back in (this generates new session tokens)

2. **Rotate Credentials**:
   - Change your Slack password
   - Review workspace audit logs for suspicious activity
   - Contact workspace admins if needed

3. **Update Repository**:
   - If committed to git, use `git filter-branch` or BFG Repo-Cleaner
   - Force push to remote (if you have permission)
   - Notify collaborators to re-clone the repository

### Alternatives to Session Tokens

For production use, consider:

1. **Slack Bot Tokens**: Create a proper Slack App with bot tokens
2. **OAuth Flow**: Implement proper OAuth for user delegation
3. **Webhooks**: Use incoming webhooks for posting messages (limited functionality)
4. **Slack SDK**: Use official SDKs with proper authentication

### Additional Resources

- [Slack API Token Types](https://api.slack.com/authentication/token-types)
- [Slack App Security Best Practices](https://api.slack.com/authentication/best-practices)
- [OWASP Credential Management](https://cheatsheetseries.owasp.org/cheatsheets/Credential_Storage_Cheat_Sheet.html)

---

**Remember**: This tool is designed for **testing and development only**. Session tokens are a workaround, not a production authentication method.
