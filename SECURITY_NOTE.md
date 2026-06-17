# 🔐 Security Notice - Secrets Management

## ⚠️ IMPORTANT: Never Commit Real Secrets to Git!

### What Happened
GitHub blocked your push because `.env.production` contained real HuggingFace and Docker Hub tokens. This is a **security feature** that protects you from accidentally exposing secrets.

### ✅ Fixed
The `.env.production` file now contains only **placeholders** and **documentation**. Real secrets go in **GitHub Secrets**.

---

## 🛡️ Where Secrets Should Go

### ❌ NEVER Put Secrets Here:
- `.env.production` (tracked by git)
- `.env` (add to `.gitignore` if you use it locally)
- Any file tracked by git
- Commit messages
- Pull request descriptions
- Issue comments

### ✅ ALWAYS Put Secrets Here:
- **GitHub Secrets** (Repository → Settings → Secrets and variables → Actions)
- Local `.env` file (not tracked by git)
- Secure password manager
- Server environment variables (directly on server)

---

## 📋 Correct Workflow

### For GitHub Actions Deployment:
1. **Create GitHub Secret**: Add `HF_TOKEN` with actual value
2. **Template File**: `.env.production` has placeholder: `HF_TOKEN=your-token-here`
3. **Workflow Uses Secret**: `.github/workflows/deploy.yml` uses `${{ secrets.HF_TOKEN }}`

### For Local Development:
1. **Copy template**: `cp .env.example .env`
2. **Add real secrets**: Edit `.env` with actual values
3. **Never commit**: `.env` is in `.gitignore`

---

## 🔍 Files That Should NOT Contain Secrets

These files are tracked by git and should NEVER contain real secrets:

- `.env.production` ← Template only
- `.env.example` ← Template only
- `docker-compose.yml` ← Use `env_file` or environment substitution
- Any `.md` documentation file
- Any source code file

---

## 🚨 If You Accidentally Commit Secrets

### If Not Yet Pushed:
```bash
# Amend last commit
git add file-with-fixed-content
git commit --amend --no-edit
```

### If Already Pushed:
```bash
# Fix the file
git add file-with-fixed-content
git commit --amend --no-edit

# Force push (rewrites history)
git push --force
```

### Critical: Revoke Exposed Secrets
Even if you remove from git, the secret is **compromised**. You MUST:

1. **HuggingFace Tokens**: Go to https://huggingface.co/settings/tokens → Revoke old token → Create new one
2. **Docker Hub Tokens**: Go to Docker Hub → Account Settings → Security → Revoke token → Create new one
3. **API Keys**: Revoke and regenerate from the service provider
4. **Passwords**: Change immediately

---

## ✅ Security Checklist

### Before Committing:
- [ ] Check `git diff` for secrets
- [ ] Ensure `.env` is in `.gitignore`
- [ ] Use placeholders in template files
- [ ] Real secrets only in GitHub Secrets

### For This Project:
- [ ] `.env.production` has NO real tokens ✅ (fixed)
- [ ] `.env` is in `.gitignore` ✅
- [ ] All secrets are in GitHub Secrets ✅ (your action needed)
- [ ] Old exposed tokens are revoked ⚠️ (action needed)

---

## 🔐 Recommended: Revoke Your Exposed Tokens

Since the tokens were in the commit (even though GitHub blocked the push), it's safer to revoke and create new ones:

### 1. Revoke HuggingFace Tokens
https://huggingface.co/settings/tokens
- Click on the token you used
- Click "Revoke"
- Create new token
- Add new token to GitHub Secrets

### 2. Revoke Docker Hub Token
https://hub.docker.com/settings/security
- Find the token
- Click "Delete"
- Create new access token
- Add new token to GitHub Secrets

---

## 📚 Learn More

- [GitHub Secret Scanning](https://docs.github.com/code-security/secret-scanning)
- [GitHub Secrets Best Practices](https://docs.github.com/actions/security-guides/security-hardening-for-github-actions)
- [Removing Sensitive Data from Git](https://docs.github.com/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)

---

## 🎯 Summary

**Golden Rule**: If a file is tracked by git (not in `.gitignore`), it should NEVER contain real secrets.

**For this project**: All secrets go in **GitHub Secrets**, not in `.env.production`.
