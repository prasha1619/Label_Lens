import React, { useState, useEffect } from 'react';
import { Scale, BookOpen, CheckCircle2, ShieldAlert, FileText, Info } from 'lucide-react';
import { ProductCategory, CategorySummary } from '../types/rules';
import { rulesService } from '../services/rulesService';
import { LegalDisclaimerBanner } from '../components/common/LegalDisclaimerBanner';

export const RulesPage: React.FC = () => {
  const [categories, setCategories] = useState<CategorySummary[]>([]);
  const [selectedCatId, setSelectedCatId] = useState<string>('packaged_commodity');
  const [activeCategory, setActiveCategory] = useState<ProductCategory | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCategories();
  }, []);

  useEffect(() => {
    if (selectedCatId) {
      fetchCategoryDetails(selectedCatId);
    }
  }, [selectedCatId]);

  const fetchCategories = async () => {
    try {
      const data = await rulesService.getCategories();
      setCategories(data);
      if (data.length > 0) {
        setSelectedCatId(data[0].category_id);
      }
    } catch (e) {
      console.error('Failed to load rule categories:', e);
    }
  };

  const fetchCategoryDetails = async (catId: string) => {
    try {
      setLoading(true);
      const data = await rulesService.getCategoryRules(catId);
      setActiveCategory(data);
    } catch (e) {
      console.error('Failed to load category rules:', e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      
      {/* Header */}
      <div className="space-y-1.5">
        <div className="flex items-center space-x-2">
          <Scale className="w-6 h-6 text-emerald-400" />
          <h1 className="text-2xl font-extrabold text-white tracking-tight">
            Legal Metrology Compliance Rule Engine
          </h1>
        </div>
        <p className="text-xs text-slate-400">
          Statutory rule definitions, mandatory declaration mandates, and confidence thresholds under the Legal Metrology (Packaged Commodities) Rules, 2011.
        </p>
      </div>

      {/* Category Tabs */}
      <div className="flex flex-wrap gap-2 pb-2 border-b border-slate-800">
        {categories.map((cat) => {
          const isSelected = selectedCatId === cat.category_id;
          return (
            <button
              key={cat.category_id}
              onClick={() => setSelectedCatId(cat.category_id)}
              className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                isSelected
                  ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 shadow-sm'
                  : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              {cat.display_name} ({cat.rule_count})
            </button>
          );
        })}
      </div>

      {/* Category Overview */}
      {activeCategory && (
        <div className="space-y-6">
          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-1">
            <h3 className="text-base font-bold text-white">{activeCategory.display_name}</h3>
            <p className="text-xs text-slate-400">{activeCategory.description}</p>
          </div>

          {/* Rules List */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {activeCategory.rules.map((rule) => (
              <div
                key={rule.rule_id}
                className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-3 hover:border-slate-700 transition-colors shadow-lg"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-[10px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                      {rule.rule_id}
                    </span>
                    <h4 className="text-sm font-bold text-slate-100 mt-1.5">{rule.title}</h4>
                  </div>
                  <span className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded ${rule.is_mandatory ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' : 'bg-slate-800 text-slate-400'}`}>
                    {rule.is_mandatory ? 'MANDATORY' : 'OPTIONAL'}
                  </span>
                </div>

                <div className="text-xs text-slate-300 bg-slate-950/60 p-3 rounded-xl border border-slate-800/80 space-y-1.5">
                  <p className="font-mono text-[10px] text-teal-400 font-semibold">{rule.legal_reference}</p>
                  <p className="leading-relaxed text-slate-300">{rule.description}</p>
                </div>

                <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-400 pt-1">
                  <div className="p-2 rounded-lg bg-slate-950/40 border border-slate-800/60">
                    <span className="text-slate-500 block text-[9px]">Pass Threshold</span>
                    <span className="text-emerald-400 font-bold">&ge; {rule.min_confidence_pass}% Conf</span>
                  </div>
                  <div className="p-2 rounded-lg bg-slate-950/40 border border-slate-800/60">
                    <span className="text-slate-500 block text-[9px]">Warning Threshold</span>
                    <span className="text-amber-400 font-bold">&ge; {rule.min_confidence_warning}% Conf</span>
                  </div>
                </div>

                <div className="text-[11px] text-slate-400 italic bg-slate-950/30 p-2.5 rounded-lg border border-slate-800/40">
                  <b className="text-slate-300 not-italic">Recommendation: </b>
                  {rule.recommendation_template}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <LegalDisclaimerBanner />

    </div>
  );
};
