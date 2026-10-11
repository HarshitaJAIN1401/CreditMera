import React, { useState } from 'react';
import {
  FileCheck,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Lock,
  Upload,
  FileCode,
} from 'lucide-react';
import { useTranslation } from '../i18n/I18nContext';
import { verifyReceiptRecord } from '../services/api';
import type { ReceiptVerifyResponse } from '../types';

export const ReceiptVerifyTab: React.FC = () => {
  const { t } = useTranslation();

  const [activeInputTab, setActiveInputTab] = useState<'upload' | 'paste'>('paste');
  const [payloadText, setPayloadText] = useState('');
  const [signatureText, setSignatureText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ReceiptVerifyResponse | null>(null);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const uploadedFile = e.target.files?.[0];
    if (!uploadedFile) return;

    setError(null);
    setResult(null);

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = event.target?.result as string;
        const parsed = JSON.parse(text);

        // Check if the file is a full receipt JSON containing receipt_payload and receipt_signature
        if (parsed.receipt_payload && parsed.receipt_signature) {
          setPayloadText(JSON.stringify(parsed.receipt_payload, null, 2));
          setSignatureText(parsed.receipt_signature);
        } else if (parsed.receipt_signature) {
          setSignatureText(parsed.receipt_signature);
          delete parsed.receipt_signature;
          setPayloadText(JSON.stringify(parsed, null, 2));
        } else {
          setPayloadText(JSON.stringify(parsed, null, 2));
        }
      } catch (err: any) {
        setError(`Failed to parse uploaded JSON file: ${err.message}`);
      }
    };
    reader.readAsText(uploadedFile);
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);

    if (!payloadText.trim()) {
      setError('Please provide the canonical receipt payload JSON.');
      return;
    }
    if (!signatureText.trim()) {
      setError('Please provide the HMAC-SHA256 receipt signature.');
      return;
    }

    let parsedPayload: Record<string, any>;
    try {
      parsedPayload = JSON.parse(payloadText.trim());
      if (typeof parsedPayload !== 'object' || parsedPayload === null || Array.isArray(parsedPayload)) {
        throw new Error('Payload must be a JSON object dictionary');
      }
    } catch (err: any) {
      setError(`Invalid JSON payload format: ${err?.message}`);
      return;
    }

    setLoading(true);
    try {
      const response = await verifyReceiptRecord(parsedPayload, signatureText.trim());
      setResult(response);
    } catch (err: any) {
      setError(err?.message || 'Receipt verification request failed.');
    } finally {
      setLoading(false);
    }
  };

  const loadSampleReceipt = () => {
    const sample = {
      receipt_number: 'CRMR-REC-SAMPLE-0001',
      asset_id: 1020304050,
      issuer: 'CreditMera Ownership Authority v1.0',
      algorithm_version: 'v1.0-dct-svd',
      payload_version: 'v1.0-128bit-hmac32',
      issued_at: '2026-10-10T12:00:00Z',
      original_file_sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      watermarked_file_sha256: 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb',
      owner_declaration_summary: 'Sole author and copyright holder.',
      legal_disclaimer: 'This cryptographic receipt certifies registration timestamp and metadata integrity.',
    };
    setPayloadText(JSON.stringify(sample, null, 2));
    setSignatureText('sample_mock_signature_for_testing_authentication_tamper_detection');
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-blue-100 rounded-lg text-blue-600">
              <FileCheck className="w-5 h-5" />
            </div>
            <h1 className="text-xl font-bold text-slate-900">
              {t('receipts_title', 'Receipt Authenticity Verifier')}
            </h1>
          </div>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">
            {t(
              'receipts_subtitle',
              'Public standalone verification of HMAC-SHA256 registration receipts issued by CreditMera.'
            )}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded bg-slate-100 text-slate-700 border border-slate-200">
            HMAC-SHA256 Signed
          </span>
        </div>
      </div>

      <div className="max-w-2xl mx-auto bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 space-y-6 shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Lock className="w-4 h-4 text-blue-600" />
            <h2 className="text-sm font-bold text-slate-900">
              Cryptographic Receipt Verification
            </h2>
          </div>
          <button
            type="button"
            onClick={loadSampleReceipt}
            className="text-xs text-blue-600 hover:text-blue-700 font-medium transition-colors"
          >
            Load Sample Template
          </button>
        </div>

        {/* Tab Selector: Upload File vs Paste JSON */}
        <div className="flex p-1 bg-slate-100 rounded-xl text-xs font-semibold text-slate-600">
          <button
            type="button"
            onClick={() => setActiveInputTab('paste')}
            className={`flex-1 py-1.5 rounded-lg transition-all flex items-center justify-center gap-1.5 ${
              activeInputTab === 'paste' ? 'bg-white text-blue-700 shadow-xs' : 'hover:text-slate-900'
            }`}
          >
            <FileCode className="w-3.5 h-3.5" />
            <span>{t('receipts_paste_tab', 'Paste JSON Payload')}</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveInputTab('upload')}
            className={`flex-1 py-1.5 rounded-lg transition-all flex items-center justify-center gap-1.5 ${
              activeInputTab === 'upload' ? 'bg-white text-blue-700 shadow-xs' : 'hover:text-slate-900'
            }`}
          >
            <Upload className="w-3.5 h-3.5" />
            <span>{t('receipts_upload_tab', 'Upload Receipt JSON')}</span>
          </button>
        </div>

        {activeInputTab === 'upload' && (
          <div className="p-4 border-2 border-dashed border-slate-300 rounded-xl text-center bg-slate-50/50">
            <Upload className="w-8 h-8 text-slate-400 mx-auto mb-2" />
            <label className="text-xs font-semibold text-blue-600 hover:underline cursor-pointer">
              {t('receipts_choose_file', 'Choose a receipt .json file')}
              <input
                type="file"
                accept=".json,application/json"
                onChange={handleFileUpload}
                className="hidden"
              />
            </label>
            <p className="text-[11px] text-slate-400 mt-1">
              Loads payload and signature automatically
            </p>
          </div>
        )}

        <form onSubmit={handleVerify} className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">
              {t('receipts_payload_label', 'Canonical Receipt Payload (JSON) *')}
            </label>
            <textarea
              required
              rows={6}
              value={payloadText}
              onChange={(e) => setPayloadText(e.target.value)}
              placeholder='{\n  "asset_id": 1020304050,\n  "receipt_number": "CRMR-REC-...",\n  "issuer": "CreditMera Ownership Authority v1.0",\n  ...\n}'
              className="w-full p-3 text-xs bg-slate-50 border border-slate-200 rounded-xl text-slate-900 font-mono placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">
              {t('receipts_sig_label', 'HMAC-SHA256 Receipt Signature (Hex) *')}
            </label>
            <input
              type="text"
              required
              value={signatureText}
              onChange={(e) => setSignatureText(e.target.value)}
              placeholder="e.g. 7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069"
              className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl text-slate-900 font-mono placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {error && (
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md shadow-blue-500/10 flex items-center justify-center gap-2 transition-all disabled:opacity-50"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <>
                <FileCheck className="w-4 h-4" />
                <span>{t('receipts_btn_verify', 'Verify HMAC Signature & Ledger Match')}</span>
              </>
            )}
          </button>
        </form>

        {/* Verification Result */}
        {result && (
          <div className="pt-4 border-t border-slate-200 space-y-4">
            <div
              className={`p-4 rounded-xl border flex items-start gap-3 ${
                result.signature_valid
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                  : 'bg-rose-50 border-rose-200 text-rose-800'
              }`}
            >
              {result.signature_valid ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
              ) : (
                <XCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
              )}
              <div>
                <h3 className="text-sm font-bold">
                  {result.signature_valid
                    ? t('receipts_valid_title', 'Receipt Signature Authentic & Valid')
                    : t('receipts_invalid_title', 'Invalid or Tampered Receipt Signature')}
                </h3>
                <p className="text-xs mt-0.5 opacity-90 leading-relaxed">{result.details}</p>
              </div>
            </div>

            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2 text-xs font-mono">
              <div className="flex justify-between">
                <span className="text-slate-500 font-medium">HMAC-SHA256 Signature:</span>
                <span className={result.signature_valid ? 'text-emerald-700 font-bold' : 'text-rose-700 font-bold'}>
                  {result.signature_valid ? 'AUTHENTIC MATCH' : 'FAILED / TAMPERED'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 font-medium">Database Ledger Record:</span>
                <span className={result.database_match ? 'text-emerald-700 font-bold' : 'text-slate-600'}>
                  {result.database_match ? 'CONFIRMED MATCH' : 'NOT FOUND IN DB'}
                </span>
              </div>
              {result.receipt_number && (
                <div className="flex justify-between">
                  <span className="text-slate-500 font-medium">Receipt Serial:</span>
                  <span className="text-slate-800 font-bold">{result.receipt_number}</span>
                </div>
              )}
              {result.registered_title && (
                <div className="flex justify-between">
                  <span className="text-slate-500 font-medium">Registered Title:</span>
                  <span className="text-slate-900 font-sans font-bold">{result.registered_title}</span>
                </div>
              )}
            </div>

            <p className="text-[11px] text-slate-400 italic leading-snug">
              {t(
                'receipts_disclaimer',
                'Cryptographic receipt verification proves data integrity with respect to the CreditMera platform key and does not constitute a judicial title.'
              )}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
