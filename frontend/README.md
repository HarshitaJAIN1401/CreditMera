# CreditMera Frontend

> **React 18 + TypeScript + Vite + Tailwind CSS**  
> *The modern, responsive web application for CreditMera — an image ownership watermarking and verification platform.*

## 🌐 Live Deployments

- **Live Production Web Application:** [https://creditmera-1.onrender.com](https://creditmera-1.onrender.com)
- **Connected Backend API:** [https://creditmera.onrender.com](https://creditmera.onrender.com)
- **Interactive API Documentation:** [https://creditmera.onrender.com/docs](https://creditmera.onrender.com/docs)
- **Main Repository:** [https://github.com/HarshitaJAIN1401/CreditMera](https://github.com/HarshitaJAIN1401/CreditMera)

---

## 🚀 Key Modules & Workspaces

1. **Dashboard (`DashboardTab.tsx`):** Creator overview with KPI cards, verification benchmark rate (100%), and recent registered assets.
2. **Protect & Embed (`ProtectTab.tsx`):** 4-step guided wizard for imperceptible DCT-SVD watermark embedding with real-time PSNR/SSIM metrics.
3. **Verify & Inspect (`VerifyTab.tsx`):** Blind forensic watermark extraction and 5-tier ownership authenticity matching.
4. **Asset Vault (`AssetVaultTab.tsx`):** Creator asset gallery with 64-bit pHash Hamming distance similarity search.
5. **Image Forensics Lab (`RobustnessLabTab.tsx`):** Interactive laboratory demonstrating 336 empirical attack trials (JPEG, blur, noise, cropping, resizing, rotation).
6. **Global Cases (`GlobalCasesTab.tsx`):** Intellectual property dispute management dossiers with chronological evidence timelines.
7. **Receipt Verifier (`ReceiptVerifyTab.tsx`):** Public cryptographic tool for validating canonical HMAC-SHA256 registration receipts.
8. **Internationalization & Arabic RTL (`I18nContext.tsx`):** Seamless localized experience across 7 languages (EN, HI, ES, FR, DE, JA, AR) with full Right-to-Left bidirectional layout support.

---

## 🛠️ Local Development

### 1. Prerequisites
- Node.js 18+ or 20+
- npm 9+

### 2. Install Dependencies
```bash
npm ci
```

### 3. Start Development Server
```bash
npm run dev
```
Access the application locally at `http://localhost:5173`.

### 4. Run Automated Test Suite
```bash
npm test -- --run
```
Executes 24 automated Vitest tests covering API services, UI components, and multi-language parity.

### 5. Build for Production
```bash
npm run build
```
Generates optimized static production bundle in `dist/`.
