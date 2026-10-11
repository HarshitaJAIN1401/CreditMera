import React, { useState, useEffect } from 'react';
import {
  Globe,
  Plus,
  Search,
  Clock,
  AlertCircle,
  Download,
  Send,
  MessageSquare,
  ShieldCheck,
  ChevronRight,
  X,
} from 'lucide-react';
import { useTranslation } from '../i18n/I18nContext';
import { useAuth } from '../context/AuthContext';
import {
  listCases,
  getCaseDetail,
  createCase,
  updateCaseStatus,
  addCaseNote,
  getCaseReport,
  listAssets,
} from '../services/api';
import type { GlobalCase, CaseStatus, AssetSummary, CaseReport } from '../types';

const STATUS_OPTIONS: CaseStatus[] = [
  'New',
  'Potential Match',
  'Evidence Collected',
  'Contacted',
  'Under Review',
  'Resolved',
  'Closed',
];

const COUNTRIES = [
  'All',
  'United States',
  'India',
  'United Kingdom',
  'Germany',
  'France',
  'Japan',
  'Canada',
  'Australia',
  'Brazil',
  'Other',
];

interface GlobalCasesTabProps {
  onNavigateToVerify?: (assetId?: number) => void;
  initialCreateAssetId?: number;
  initialSuspectedUrl?: string;
  initialMatchScore?: number;
  initialWatermarkStatus?: string;
}

export const GlobalCasesTab: React.FC<GlobalCasesTabProps> = ({
  onNavigateToVerify: _onNavigateToVerify,
  initialCreateAssetId,
  initialSuspectedUrl,
  initialMatchScore,
  initialWatermarkStatus,
}) => {
  const { t } = useTranslation();
  const { token, isAuthenticated } = useAuth();

  const [cases, setCases] = useState<GlobalCase[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedCase, setSelectedCase] = useState<GlobalCase | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Filters
  const [selectedStatus, setSelectedStatus] = useState<string>('All');
  const [selectedCountry, setSelectedCountry] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState('');

  // Create Case Modal
  const [createModalOpen, setCreateModalOpen] = useState(Boolean(initialCreateAssetId));
  const [userAssets, setUserAssets] = useState<AssetSummary[]>([]);
  const [selectedAssetId, setSelectedAssetId] = useState<number | ''>(initialCreateAssetId || '');
  const [caseTitle, setCaseTitle] = useState('');
  const [suspectedUrl, setSuspectedUrl] = useState(initialSuspectedUrl || '');
  const [suspectedCountry, setSuspectedCountry] = useState('United States');
  const [evidenceNotes, setEvidenceNotes] = useState('');
  const [suspectedFile, setSuspectedFile] = useState<File | null>(null);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Note form state
  const [newNote, setNewNote] = useState('');
  const [submittingNote, setSubmittingNote] = useState(false);

  useEffect(() => {
    if (token) {
      loadCases();
      listAssets(token, 0, 50)
        .then((data) => setUserAssets(data))
        .catch(() => {});
    }
  }, [token, selectedStatus, selectedCountry]);

  const loadCases = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await listCases(
        token,
        selectedStatus === 'All' ? undefined : selectedStatus,
        selectedCountry === 'All' ? undefined : selectedCountry
      );
      setCases(data);
    } catch (err) {
      console.error('Failed to load cases:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenCaseDetail = async (c: GlobalCase) => {
    if (!token) return;
    setSelectedCase(c);
    setDetailLoading(true);
    try {
      const detail = await getCaseDetail(c.id, token);
      setSelectedCase(detail);
    } catch (err) {
      console.error('Failed to refresh case detail:', err);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !selectedAssetId || !caseTitle.trim()) {
      setCreateError('Please enter a title and select a protected asset.');
      return;
    }
    setCreating(true);
    setCreateError(null);
    try {
      const newCase = await createCase(
        {
          title: caseTitle,
          assetId: Number(selectedAssetId),
          suspectedUrl: suspectedUrl || undefined,
          suspectedCountry: suspectedCountry || undefined,
          matchScore: initialMatchScore,
          watermarkStatus: initialWatermarkStatus,
          evidenceNotes: evidenceNotes || undefined,
          suspectedFile: suspectedFile || undefined,
        },
        token
      );
      setCases([newCase, ...cases]);
      setSelectedCase(newCase);
      setCreateModalOpen(false);
      setCaseTitle('');
      setSuspectedUrl('');
      setEvidenceNotes('');
      setSuspectedFile(null);
    } catch (err: any) {
      setCreateError(err.message || 'Failed to open case');
    } finally {
      setCreating(false);
    }
  };

  const handleStatusUpdate = async (status: CaseStatus) => {
    if (!selectedCase || !token) return;
    try {
      const updated = await updateCaseStatus(
        selectedCase.id,
        status,
        `Status changed to ${status}`,
        token
      );
      setSelectedCase(updated);
      setCases(cases.map((c) => (c.id === updated.id ? updated : c)));
    } catch (err) {
      console.error('Failed to update case status:', err);
    }
  };

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCase || !token || !newNote.trim()) return;
    setSubmittingNote(true);
    try {
      const updated = await addCaseNote(selectedCase.id, newNote.trim(), token);
      setSelectedCase(updated);
      setCases(cases.map((c) => (c.id === updated.id ? updated : c)));
      setNewNote('');
    } catch (err) {
      console.error('Failed to add case note:', err);
    } finally {
      setSubmittingNote(false);
    }
  };

  const handleDownloadReport = async () => {
    if (!selectedCase || !token) return;
    try {
      const report: CaseReport = await getCaseReport(selectedCase.id, token);
      const blob = new Blob([JSON.stringify(report, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `case_report_${selectedCase.case_number}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to download report:', err);
    }
  };

  const filteredCases = cases.filter(
    (c) =>
      c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.case_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.asset_title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-blue-100 rounded-lg text-blue-600">
              <Globe className="w-5 h-5" />
            </div>
            <h1 className="text-xl font-bold text-slate-900">
              {t('cases_title', 'Global Case Management')}
            </h1>
          </div>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">
            {t(
              'cases_subtitle',
              'Track unauthorized image use across borders, preserve chain of custody, and record legal attribution notices.'
            )}
          </p>
        </div>

        <button
          onClick={() => setCreateModalOpen(true)}
          className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 shadow-sm transition-colors self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>{t('cases_btn_new', 'Open New Case')}</span>
        </button>
      </div>

      {!isAuthenticated ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center shadow-xs">
          <Globe className="w-12 h-12 text-blue-500 mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-900">Sign in to manage global cases</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
            Build forensic evidence dossiers for unauthorized usage discovered online.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
            <div className="relative flex-1 max-w-xs">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search case #, title or asset..."
                className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {/* Status Filter */}
              <div className="flex items-center gap-1">
                <span className="text-[11px] font-medium text-slate-400">Status:</span>
                <select
                  value={selectedStatus}
                  onChange={(e) => setSelectedStatus(e.target.value)}
                  className="py-1 px-2 text-xs bg-white border border-slate-200 rounded-lg text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="All">All Statuses</option>
                  {STATUS_OPTIONS.map((st) => (
                    <option key={st} value={st}>
                      {st}
                    </option>
                  ))}
                </select>
              </div>

              {/* Country Filter */}
              <div className="flex items-center gap-1">
                <span className="text-[11px] font-medium text-slate-400">Country:</span>
                <select
                  value={selectedCountry}
                  onChange={(e) => setSelectedCountry(e.target.value)}
                  className="py-1 px-2 text-xs bg-white border border-slate-200 rounded-lg text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {COUNTRIES.map((ct) => (
                    <option key={ct} value={ct}>
                      {ct}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Cases List */}
          {loading ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-16 text-center">
              <div className="inline-block w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin mb-3" />
              <p className="text-xs text-slate-500">Loading cases...</p>
            </div>
          ) : filteredCases.length === 0 ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center shadow-xs">
              <Globe className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <h3 className="text-sm font-bold text-slate-800">
                {t('cases_empty_title', 'No active cases')}
              </h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-4">
                {t(
                  'cases_empty_desc',
                  'No dossiers created yet. Open a case when you discover uncredited copies online.'
                )}
              </p>
              <button
                onClick={() => setCreateModalOpen(true)}
                className="px-3.5 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 transition-colors"
              >
                {t('cases_btn_new', 'Open New Case')}
              </button>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-start text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                    <tr>
                      <th className="py-3 px-4 text-start">{t('cases_col_case_no', 'Case No')}</th>
                      <th className="py-3 px-4 text-start">{t('cases_col_title', 'Title & Context')}</th>
                      <th className="py-3 px-4 text-start">{t('cases_col_asset', 'Protected Asset')}</th>
                      <th className="py-3 px-4 text-start">{t('cases_col_country', 'Country')}</th>
                      <th className="py-3 px-4 text-start">{t('cases_col_evidence', 'Evidence')}</th>
                      <th className="py-3 px-4 text-start">{t('cases_col_status', 'Status')}</th>
                      <th className="py-3 px-4 text-end">{t('cases_col_action', 'Action')}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {filteredCases.map((c) => (
                      <tr
                        key={c.id}
                        className="hover:bg-slate-50/80 transition-colors cursor-pointer"
                        onClick={() => handleOpenCaseDetail(c)}
                      >
                        <td className="py-3 px-4 font-mono font-bold text-blue-700 whitespace-nowrap">
                          {c.case_number}
                        </td>
                        <td className="py-3 px-4">
                          <p className="font-semibold text-slate-900 line-clamp-1">{c.title}</p>
                          {c.suspected_url && (
                            <p className="text-[11px] text-slate-400 truncate max-w-xs">
                              {c.suspected_url}
                            </p>
                          )}
                        </td>
                        <td className="py-3 px-4 font-medium text-slate-800">
                          {c.asset_title}
                        </td>
                        <td className="py-3 px-4 whitespace-nowrap">
                          <span className="flex items-center gap-1 text-slate-600">
                            <Globe className="w-3.5 h-3.5 text-slate-400" />
                            {c.suspected_country || 'Global'}
                          </span>
                        </td>
                        <td className="py-3 px-4 whitespace-nowrap">
                          <div className="flex items-center gap-1.5">
                            {c.watermark_status && (
                              <span
                                className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                                  c.watermark_status === 'MATCHED'
                                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                    : 'bg-slate-100 text-slate-600'
                                }`}
                              >
                                {c.watermark_status}
                              </span>
                            )}
                            {c.match_score !== null && c.match_score !== undefined && (
                              <span className="text-[10px] font-mono font-medium text-purple-700">
                                {(c.match_score * 100).toFixed(0)}% sim
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-3 px-4 whitespace-nowrap">
                          <span
                            className={`text-[10px] font-semibold px-2.5 py-0.5 rounded-full ${
                              c.status === 'Resolved'
                                ? 'bg-emerald-100 text-emerald-800'
                                : c.status === 'Potential Match'
                                ? 'bg-amber-100 text-amber-800'
                                : c.status === 'Evidence Collected'
                                ? 'bg-blue-100 text-blue-800'
                                : 'bg-slate-100 text-slate-700'
                            }`}
                          >
                            {c.status}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-end whitespace-nowrap">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenCaseDetail(c);
                            }}
                            className="p-1.5 text-slate-400 hover:text-blue-600 rounded-lg hover:bg-slate-100 transition-colors"
                            title="View dossier"
                          >
                            <ChevronRight className="w-4 h-4 rtl:rotate-180" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Case Detail Slideover / Modal */}
      {selectedCase && (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-slate-900/50 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="w-full max-w-2xl h-full bg-white shadow-2xl flex flex-col border-s border-slate-200 overflow-hidden">
            {/* Dossier Header */}
            <div className="p-6 border-b border-slate-200 bg-slate-50 flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold text-blue-700 px-2 py-0.5 bg-blue-100 rounded">
                    {selectedCase.case_number}
                  </span>
                  <select
                    value={selectedCase.status}
                    onChange={(e) => handleStatusUpdate(e.target.value as CaseStatus)}
                    className="text-xs font-semibold py-1 px-2.5 rounded-lg border border-slate-300 bg-white text-slate-800 focus:ring-2 focus:ring-blue-500"
                  >
                    {STATUS_OPTIONS.map((st) => (
                      <option key={st} value={st}>
                        {st}
                      </option>
                    ))}
                  </select>
                </div>
                <h2 className="text-base font-bold text-slate-900 mt-2">
                  {selectedCase.title}
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Target Work: <strong className="text-slate-700">{selectedCase.asset_title}</strong> (ID #{selectedCase.asset_id})
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleDownloadReport}
                  className="p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-200/60 rounded-lg transition-colors"
                  title="Download forensic evidence JSON report"
                >
                  <Download className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setSelectedCase(null)}
                  className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Dossier Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {detailLoading && (
                <div className="p-3 bg-blue-50 text-blue-700 rounded-lg text-xs flex items-center gap-2">
                  <div className="w-3.5 h-3.5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                  Refreshing dossier chain of custody...
                </div>
              )}

              {/* Technical Evidence Overview */}
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-blue-600" />
                  {t('cases_detail_evidence_header', 'Technical Evidence Assessment')}
                </h4>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <span className="text-slate-400">Watermark Verification:</span>
                    <p className="font-semibold text-slate-800 mt-0.5">
                      {selectedCase.watermark_status || 'NOT_DETECTED'}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-400">Visual Similarity Score:</span>
                    <p className="font-semibold text-slate-800 mt-0.5">
                      {selectedCase.match_score !== null && selectedCase.match_score !== undefined
                        ? `${(selectedCase.match_score * 100).toFixed(1)}%`
                        : 'Not evaluated'}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-400">Suspected Country:</span>
                    <p className="font-semibold text-slate-800 mt-0.5">
                      {selectedCase.suspected_country || 'Unknown / International'}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-400">Created:</span>
                    <p className="font-semibold text-slate-800 mt-0.5">
                      {new Date(selectedCase.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>

                {selectedCase.suspected_url && (
                  <div className="pt-2 border-t border-slate-200 text-xs">
                    <span className="text-slate-400">Suspected Publisher URL:</span>
                    <a
                      href={selectedCase.suspected_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block font-mono text-blue-600 hover:underline break-all mt-0.5"
                    >
                      {selectedCase.suspected_url}
                    </a>
                  </div>
                )}
              </div>

              {/* Evidence Notes */}
              {selectedCase.evidence_notes && (
                <div className="space-y-1">
                  <h4 className="text-xs font-bold text-slate-800">Initial Evidence Notes</h4>
                  <div className="p-3 bg-white rounded-xl border border-slate-200 text-xs text-slate-700 leading-relaxed whitespace-pre-wrap">
                    {selectedCase.evidence_notes}
                  </div>
                </div>
              )}

              {/* Interactive Timeline */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                  <Clock className="w-4 h-4 text-slate-500" />
                  {t('cases_detail_timeline_header', 'Dossier Timeline & Chain of Custody')}
                </h4>

                <div className="relative border-s border-slate-200 ms-3 space-y-4">
                  {(selectedCase.timeline || []).map((item, idx) => (
                    <div key={idx} className="ms-4 relative">
                      <span className="absolute -start-6.5 top-1 w-2.5 h-2.5 rounded-full bg-blue-600 ring-4 ring-white" />
                      <div className="p-3 bg-white border border-slate-200 rounded-xl shadow-xs">
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="font-bold text-slate-800">{item.action}</span>
                          <span className="text-slate-400">
                            {new Date(item.timestamp).toLocaleString()}
                          </span>
                        </div>
                        {item.details && (
                          <p className="text-xs text-slate-600 mt-1">{item.details}</p>
                        )}
                        <span className="text-[10px] text-slate-400 mt-1 block">
                          By: {item.actor}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Add Note Form */}
              <form onSubmit={handleAddNote} className="space-y-2 pt-2">
                <label className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                  <MessageSquare className="w-3.5 h-3.5 text-blue-600" />
                  {t('cases_detail_add_note', 'Add Note / Correspondence Record')}
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newNote}
                    onChange={(e) => setNewNote(e.target.value)}
                    placeholder={t('cases_detail_note_placeholder', 'Document DMCA sent, email received, or evidence update...')}
                    className="flex-1 px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    type="submit"
                    disabled={submittingNote || !newNote.trim()}
                    className="px-3.5 py-2 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center gap-1"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>Add</span>
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Create Case Modal */}
      {createModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="relative w-full max-w-lg bg-white rounded-2xl shadow-2xl border border-slate-200 p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <Globe className="w-5 h-5 text-blue-600" />
                <h3 className="text-base font-bold text-slate-900">
                  {t('cases_btn_new', 'Open New Global Case')}
                </h3>
              </div>
              <button
                onClick={() => setCreateModalOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-700 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {createError && (
              <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{createError}</span>
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Case Title *
                </label>
                <input
                  type="text"
                  required
                  value={caseTitle}
                  onChange={(e) => setCaseTitle(e.target.value)}
                  placeholder="e.g., Unauthorized commercial use on foreign e-commerce catalog"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Associated Protected Asset *
                </label>
                <select
                  required
                  value={selectedAssetId}
                  onChange={(e) => setSelectedAssetId(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select a registered image...</option>
                  {userAssets.map((a) => (
                    <option key={a.asset_id} value={a.asset_id}>
                      #{a.asset_id} - {a.title} ({a.original_filename})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Suspected Country
                  </label>
                  <select
                    value={suspectedCountry}
                    onChange={(e) => setSuspectedCountry(e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {COUNTRIES.filter((c) => c !== 'All').map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Suspected Online URL
                  </label>
                  <input
                    type="url"
                    value={suspectedUrl}
                    onChange={(e) => setSuspectedUrl(e.target.value)}
                    placeholder="https://example.com/image.jpg"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Upload Suspected Image Sample (Optional)
                </label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setSuspectedFile(e.target.files?.[0] || null)}
                  className="w-full text-xs text-slate-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Evidence Notes &amp; Discovery Context
                </label>
                <textarea
                  rows={3}
                  value={evidenceNotes}
                  onChange={(e) => setEvidenceNotes(e.target.value)}
                  placeholder="Where was this observed? Note infringer details or DMCA tracking..."
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setCreateModalOpen(false)}
                  className="px-3.5 py-2 text-slate-600 hover:bg-slate-100 rounded-lg font-medium transition-colors"
                >
                  {t('common_cancel', 'Cancel')}
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold shadow-sm transition-colors disabled:opacity-50"
                >
                  {creating ? 'Opening Case...' : 'Create Case Dossier'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
