import React from 'react';

import { useLanguage } from '../contexts/LanguageContext';

// Import images
import salahImg from '../assets/team/salah.jpeg';
import abdelazizImg from '../assets/team/abdelaziz.jpeg';
import ahmedImg from '../assets/team/ahmed.jpeg';
import amiraImg from '../assets/team/amira.jpeg';
import yomnaImg from '../assets/team/yomna.jpeg';


const GithubIcon = ({ size = 22, color = 'currentColor' }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"/>
    <path d="M9 18c-4.51 2-5-2-7-2"/>
  </svg>
);

const LinkedinIcon = ({ size = 22, color = 'currentColor' }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"/>
    <rect width="4" height="12" x="2" y="9"/>
    <circle cx="4" cy="4" r="2"/>
  </svg>
);

export default function Team() {
  const { language } = useLanguage();
  const isAr = language === 'ar';

  const team = [
    { 
      name: isAr ? 'صلاح عبد الدايم' : 'Salah Abdeldaim', 
      role: isAr ? 'قائد الفريق ومهندس ذكاء اصطناعي' : 'Team Leader & Lead AI Engineer', 
      note: isAr ? 'المسؤول عن بناء المعمارية الأساسية (MedLens AI Architecture)، وهندسة خطوط الأنابيب (RAG Pipeline)، والدمج الكامل مع (ChromaDB) ونماذج الذكاء الاصطناعي.' : 'Built the core RAG pipeline, ChromaDB integration, and the overall MedLens AI architecture.',
      img: salahImg,
      github: 'https://github.com/salahAbdeldaim',
      linkedin: 'https://www.linkedin.com/in/salah-abdeldaim'
    },
    { 
      name: isAr ? 'عبد العزيز البنا' : 'Abdelaziz Elbanna', 
      role: isAr ? 'مهندس بيانات ومسؤول التوثيق التقني' : 'Data Engineer & Tech Docs Lead', 
      note: isAr ? 'المسؤول عن معالجة ودمج وتنظيف قواعد بيانات الأدوية المصرية المعقدة، بالإضافة إلى هندسة التوثيق التقني للمشروع.' : 'Managed the complex Egyptian Pharmacology datasets (cleaning & parsing) and led the technical documentation engineering.',
      img: abdelazizImg,
      github: 'https://github.com/AbdelazizElbanna',
      linkedin: 'https://www.linkedin.com/in/abdelazizelbanna/'
    },
    { 
      name: isAr ? 'أحمد أمين' : 'Ahmed Amin', 
      role: isAr ? 'عالم بيانات ومهندس تعلم الآلة' : 'Data Scientist & ML Engineer', 
      note: isAr ? 'المسؤول عن هندسة تضمين البيانات (Embedding Optimization)، وتقييم أداء النموذج ومقاومة الهلوسة.' : 'Spearheaded the data chunking architecture, embedding optimization, and RAG evaluation metrics.',
      img: ahmedImg,
      github: 'https://github.com/AhmedAminz',
      linkedin: 'https://www.linkedin.com/in/ahmed-amin1/'
    },
    { 
      name: isAr ? 'أميرة عطية' : 'Amira Attia', 
      role: isAr ? 'مهندسة تعلم الآلة (NLP)' : 'Machine Learning Engineer (NLP)', 
      note: isAr ? 'المسؤولة عن خوارزميات معالجة اللغة الطبيعية، استخراج النوايا، وتطبيق تقنيات (Few-Shot Prompting).' : 'Designed the NLP intent extraction algorithms, query rewriting logic, and applied Few-Shot Prompting.',
      img: amiraImg,
      github: 'https://github.com/Amiraattia07',
      linkedin: 'https://www.linkedin.com/in/amira-attia-84b95b21a'
    },
    { 
      name: isAr ? 'يمنى زين الدين' : 'Yomna Zein Eldein', 
      role: isAr ? 'مهندسة ذكاء اصطناعي ومتخصصة RAG' : 'AI Engineer & RAG Specialist', 
      note: isAr ? 'المسؤولة عن بناء أدوات سحب البيانات الطبية، وتطبيق خوارزميات إعادة الترتيب (Reranking) لرفع دقة الاسترجاع.' : 'Developed the clinical data scraping pipelines and integrated Cross-Encoder reranking models to boost retrieval precision.',
      img: yomnaImg,
      github: 'https://github.com/yumnazeineldein',
      linkedin: 'https://www.linkedin.com/in/yomna-zein-eldein-'
    },
  ];

  return (
    <div style={{ padding: '40px 24px', overflowY: 'auto', height: '100%' }}>
      <div style={{ maxWidth: '1000px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '32px' }}>
        <div style={{ textAlign: 'center', marginBottom: '8px' }}>
          <h1 style={{ fontSize: '2.5rem', fontWeight: '800', color: 'var(--text)', margin: 0, textShadow: '0 2px 10px rgba(0,0,0,0.2)' }}>
            {isAr ? 'فريق العمل' : 'The Team'}
          </h1>
          <p style={{ color: 'var(--text-muted)', marginTop: '12px', fontSize: '1.15rem' }}>
            {isAr ? 'المهندسون والباحثون خلف نظام MedLens AI' : 'The core engineers and researchers behind MedLens AI.'}
          </p>
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px', paddingBottom: '40px' }}>
          {team.map((member, i) => (
            <div key={i} className="glass" style={{ 
              padding: '32px 24px', 
              borderRadius: '24px', 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: 'center', 
              textAlign: 'center', 
              border: '1px solid rgba(255,255,255,0.08)', 
              position: 'relative', 
              overflow: 'hidden',
              boxShadow: '0 8px 32px rgba(0,0,0,0.1)'
            }}>
              
              {/* Background Glow */}
              <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: '100px', background: 'linear-gradient(180deg, rgba(255,255,255,0.05), transparent)' }} />
              
              <img 
                src={member.img} 
                alt={member.name}
                style={{ width: '110px', height: '110px', borderRadius: '50%', objectFit: 'cover', border: '4px solid var(--primary)', padding: '3px', zIndex: 1, marginBottom: '20px', background: 'var(--bg)', boxShadow: '0 8px 24px rgba(0,0,0,0.2)' }}
              />
              
              <h2 style={{ fontWeight: '800', fontSize: '1.35rem', color: 'var(--text)', margin: 0 }}>{member.name}</h2>
              <div style={{ color: 'var(--primary)', fontWeight: '600', fontSize: '0.95rem', marginTop: '8px', marginBottom: '16px', letterSpacing: '0.5px' }}>{member.role}</div>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem', lineHeight: '1.7', margin: '0 0 24px 0', flex: 1 }}>{member.note}</p>
              
              <div style={{ display: 'flex', gap: '16px', marginTop: 'auto' }}>
                {member.github && (
                  <a href={member.github} target="_blank" rel="noopener noreferrer" style={{ padding: '10px', borderRadius: '12px', background: 'rgba(255,255,255,0.05)', color: 'var(--text)', transition: 'all 0.2s', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <GithubIcon size={22} />
                  </a>
                )}
                {member.linkedin && (
                  <a href={member.linkedin} target="_blank" rel="noopener noreferrer" style={{ padding: '10px', borderRadius: '12px', background: 'rgba(255,255,255,0.05)', color: 'var(--text)', transition: 'all 0.2s', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <LinkedinIcon size={22} />
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
