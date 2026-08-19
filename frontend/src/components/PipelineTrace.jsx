import React, { useState } from 'react';
import { Brain, CloudSun, Database, Sparkles, CheckCircle2, ChevronDown, ChevronUp, Code2, ArrowRight } from 'lucide-react';

export default function PipelineTrace({ trace, intent, weather, sources }) {
  const [showRawJson, setShowRawJson] = useState(false);

  if (!trace && !intent) {
    return (
      <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', textAlign: 'center', marginTop: '40px' }}>
        No pipeline trace available yet. Ask a question to see the live execution path.
      </div>
    );
  }

  const step1 = trace?.step_1_intent || intent;
  const step2 = trace?.step_2_weather || { executed: !!weather, governorate: weather?.governorate_en };
  const step3 = trace?.step_3_retrieval || { top_k_per_collection: 3, total_chunks_retrieved: sources?.length || 0 };
  const step4 = trace?.step_4_generation || { model: 'openai/gpt-oss-120b' };

  return (
    <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      
      {/* Header & Mode Toggle */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Live Execution Flow
        </div>
        <button
          onClick={() => setShowRawJson(!showRawJson)}
          style={{
            background: 'var(--surface-2)',
            border: '1px solid var(--border)',
            color: 'var(--text)',
            fontSize: '0.75rem',
            padding: '4px 8px',
            borderRadius: '6px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}
        >
          <Code2 size={12} /> {showRawJson ? 'Visual Flow' : 'Raw JSON'}
        </button>
      </div>

      {showRawJson ? (
        <pre style={{
          background: 'rgba(0,0,0,0.4)',
          border: '1px solid var(--border)',
          borderRadius: '12px',
          padding: '12px',
          fontSize: '0.75rem',
          color: 'var(--accent)',
          overflowX: 'auto',
          lineHeight: '1.4'
        }}>
          {JSON.stringify(trace || { intent, weather, sources_count: sources?.length }, null, 2)}
        </pre>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', position: 'relative' }}>
          
          {/* Step 1: Intent Extraction */}
          <div className="glass" style={{ padding: '14px', borderRadius: '12px', borderLeft: '3px solid var(--primary)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: '600', fontSize: '0.85rem', color: 'var(--text)' }}>
                <Brain size={16} color="var(--primary)" />
                1. Intent & Context Extraction
              </div>
              <span style={{ fontSize: '0.7rem', background: 'rgba(99,102,241,0.15)', color: 'var(--primary)', padding: '2px 6px', borderRadius: '4px' }}>
                Structured
              </span>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div>• <strong>Condition:</strong> <span style={{ color: 'var(--text)' }}>{step1?.condition || 'General'}</span></div>
              <div>• <strong>Governorate:</strong> <span style={{ color: 'var(--text)' }}>{step1?.governorate || 'None'}</span></div>
              <div>• <strong>Target Collections:</strong> <span style={{ color: 'var(--text)' }}>{JSON.stringify(step1?.collections_targeted || step1?.collections_to_query || [])}</span></div>
              {step1?.medications?.length > 0 && (
                <div>• <strong>Medications:</strong> <span style={{ color: 'var(--text)' }}>{step1.medications.join(', ')}</span></div>
              )}
              {step1?.intents?.length > 0 && (
                <div style={{ marginTop: '4px' }}>• <strong>Detected Intents:</strong> 
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '4px' }}>
                    {step1.intents.map((intent, idx) => (
                      <span key={idx} style={{ background: 'rgba(255,255,255,0.1)', border: '1px solid var(--border)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.7rem', color: 'var(--text)' }}>{intent}</span>
                    ))}
                  </div>
                </div>
              )}
              {step1?.clinical_summary && (
                <div style={{ marginTop: '8px', padding: '8px', background: 'rgba(0,0,0,0.15)', borderRadius: '8px', borderLeft: '2px solid var(--primary)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '2px', fontWeight: 'bold' }}>Clinical Summary (Memory):</div>
                  <div style={{ color: 'var(--text)', fontStyle: 'italic', lineHeight: '1.4' }}>"{step1.clinical_summary}"</div>
                </div>
              )}
            </div>
          </div>

          {/* Step 2: Weather Layer */}
          <div className="glass" style={{ padding: '14px', borderRadius: '12px', borderLeft: `3px solid ${step2?.executed ? 'var(--accent)' : 'var(--border)'}` }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: '600', fontSize: '0.85rem', color: 'var(--text)' }}>
                <CloudSun size={16} color={step2?.executed ? 'var(--accent)' : 'var(--text-muted)'} />
                2. Live Weather Context (Open-Meteo)
              </div>
              <span style={{ 
                fontSize: '0.7rem', 
                background: step2?.executed ? 'rgba(56,189,248,0.15)' : 'rgba(255,255,255,0.05)', 
                color: step2?.executed ? 'var(--accent)' : 'var(--text-muted)', 
                padding: '2px 6px', 
                borderRadius: '4px' 
              }}>
                {step2?.executed ? 'Fetched Live' : 'Not Requested'}
              </span>
            </div>
            {step2?.executed ? (
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div>• <strong>Location:</strong> <span style={{ color: 'var(--text)' }}>{step2.governorate}</span></div>
                {step2.live_metrics && (
                  <div>• <strong>Metrics:</strong> <span style={{ color: 'var(--text)' }}>{step2.live_metrics.temp_c}°C | {step2.live_metrics.humidity}% Humidity | UV {step2.live_metrics.uv_index}</span></div>
                )}
              </div>
            ) : (
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                No weather/location variables detected in the patient query.
              </div>
            )}
          </div>

          {/* Step 3: Vector Database Retrieval */}
          <div className="glass" style={{ padding: '14px', borderRadius: '12px', borderLeft: '3px solid var(--success)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: '600', fontSize: '0.85rem', color: 'var(--text)' }}>
                <Database size={16} color="var(--success)" />
                3. Vector Store Dense Retrieval
              </div>
              <span style={{ fontSize: '0.7rem', background: 'rgba(52,211,153,0.15)', color: 'var(--success)', padding: '2px 6px', borderRadius: '4px' }}>
                ChromaDB
              </span>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div>• <strong>Model:</strong> <span style={{ color: 'var(--text)' }}>BAAI/bge-m3 (Dense 1024-d)</span></div>
              <div>• <strong>Top-K per Collection:</strong> <span style={{ color: 'var(--text)', fontWeight: 'bold' }}>{step3?.top_k_per_collection || "N/A"}</span></div>
              <div>• <strong>Total Chunks Retrieved:</strong> <span style={{ color: 'var(--text)', fontWeight: 'bold' }}>{step3?.total_chunks_retrieved || step3?.k_candidates_retrieved || sources?.length || 0}</span></div>
              <div>• <strong>Chunks Selected for Context:</strong> <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>{step3?.k_selected_for_context || sources?.filter(s => s.is_selected).length || 0}</span></div>
              <div>• <strong>Distance Metric:</strong> <span style={{ color: 'var(--text)' }}>Cosine Similarity</span></div>
            </div>
          </div>

          {/* Step 4: LLM Generation */}
          <div className="glass" style={{ padding: '14px', borderRadius: '12px', borderLeft: '3px solid #e879f9' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: '600', fontSize: '0.85rem', color: 'var(--text)' }}>
                <Sparkles size={16} color="#e879f9" />
                4. Context Fusion & LLM Grounding
              </div>
              <span style={{ fontSize: '0.7rem', background: 'rgba(232,121,249,0.15)', color: '#e879f9', padding: '2px 6px', borderRadius: '4px' }}>
                Grounded
              </span>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div>• <strong>Inference Model:</strong> <span style={{ color: 'var(--text)' }}>{step4?.model || 'openai/gpt-oss-120b'}</span></div>
              <div>• <strong>Grounded Context Chunks:</strong> <span style={{ color: 'var(--text)' }}>{step4?.grounded_context_chunks ?? 'N/A'}</span></div>
              <div>• <strong>Patient Profile Injected:</strong> <span style={{ color: step4?.patient_profile_injected ? 'var(--success)' : 'var(--text-muted)' }}>{step4?.patient_profile_injected ? 'Yes' : 'No'}</span></div>
              <div>• <strong>Working Memory Injected:</strong> <span style={{ color: step4?.working_memory_injected ? 'var(--success)' : 'var(--text-muted)' }}>{step4?.working_memory_injected ? 'Yes' : 'No'}</span></div>
              <div>• <strong>Grounding Policy:</strong> <span style={{ color: 'var(--text)' }}>Strict Context-Bound (No hallucinations)</span></div>
            </div>
          </div>

        </div>
      )}

    </div>
  );
}
