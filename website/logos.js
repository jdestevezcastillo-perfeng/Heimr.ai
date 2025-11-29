import React, { useState } from 'react';

const HelmrBifrostVariations = () => {
  const [activeLogo, setActiveLogo] = useState(0);
  const [darkMode, setDarkMode] = useState(true);
  
  const colors = {
    primary: '#0f172a',
    accent: '#38bdf8',
    light: '#f8fafc',
    muted: '#64748b',
    // Added a slightly lighter blue for Bifrost effects
    glow: '#7dd3fc', 
  };

  // 1. ORIGINAL: The All-Seeing Eye (Your favorite)
  const OriginalEye = ({ size = 48, color = colors.accent }) => (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
      <path d="M32 12C18 12 6 32 6 32C6 32 18 52 32 52C46 52 58 32 58 32C58 32 46 12 32 12Z" stroke={color} strokeWidth="2.5" />
      <circle cx="32" cy="32" r="12" stroke={color} strokeWidth="2.5" />
      <circle cx="32" cy="32" r="5" fill={color} />
      <path d="M32 20V26" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
      <path d="M32 38V44" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
      <path d="M20 32H26" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
      <path d="M38 32H44" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );

  // 2. VARIATION: The Bifrost Beam
  // Concept: The Eye projecting the bridge upwards (connection to the cloud)
  const BifrostBeam = ({ size = 48, color = colors.accent }) => (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
      {/* The Bridge (Beam) rising up */}
      <path d="M32 32L32 4" stroke={color} strokeWidth="2" strokeLinecap="round" strokeDasharray="4 4" opacity="0.6"/>
      <path d="M24 28L18 4" stroke={color} strokeWidth="1.5" strokeLinecap="round" opacity="0.4" />
      <path d="M40 28L46 4" stroke={color} strokeWidth="1.5" strokeLinecap="round" opacity="0.4" />
      
      {/* Flattened Eye Base */}
      <path d="M6 32C6 32 18 52 32 52C46 52 58 32 58 32" stroke={color} strokeWidth="2.5" strokeLinecap="round" />
      <path d="M10 26C16 36 24 40 32 40C40 40 48 36 54 26" stroke={color} strokeWidth="1.5" strokeLinecap="round" opacity="0.5" />
      
      {/* Central Pupil */}
      <circle cx="32" cy="36" r="4" fill={color} />
      <circle cx="32" cy="36" r="8" stroke={color} strokeWidth="2" />
    </svg>
  );

  // 3. VARIATION: The Arced Bridge
  // Concept: The Bifrost acts as a protective arc/eyelid over the vision
  const BifrostArc = ({ size = 48, color = colors.accent }) => (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
      {/* The Bifrost Arcs (Rainbow Bridge) */}
      <path d="M8 28C8 28 20 8 32 8C44 8 56 28 56 28" stroke={color} strokeWidth="2.5" strokeLinecap="round" />
      <path d="M14 28C14 28 22 14 32 14C42 14 50 28 50 28" stroke={color} strokeWidth="1.5" strokeLinecap="round" opacity="0.7" />
      <path d="M20 28C20 28 25 20 32 20C39 20 44 28 44 28" stroke={color} strokeWidth="1" strokeLinecap="round" opacity="0.5" />

      {/* The Eye below looking up/out */}
      <path d="M6 32C6 32 18 52 32 52C46 52 58 32 58 32" stroke={color} strokeWidth="2.5" strokeLinecap="round" />
      
      {/* Pupil */}
      <circle cx="32" cy="34" r="5" fill={color} />
      <path d="M32 42V46" stroke={color} strokeWidth="2" strokeLinecap="round" />
    </svg>
  );

  // 4. VARIATION: The Data Stream
  // Concept: The Bifrost flowing horizontally through the eye (Movement/Speed)
  const BifrostFlow = ({ size = 48, color = colors.accent }) => (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
      {/* Flow lines (The Bridge) */}
      <path d="M4 32H60" stroke={color} strokeWidth="1" opacity="0.3" />
      <path d="M2 24H24" stroke={color} strokeWidth="2" strokeLinecap="round" />
      <path d="M40 24H62" stroke={color} strokeWidth="2" strokeLinecap="round" />
      <path d="M2 40H24" stroke={color} strokeWidth="2" strokeLinecap="round" />
      <path d="M40 40H62" stroke={color} strokeWidth="2" strokeLinecap="round" />

      {/* The Eye Shape Overlay */}
      <path d="M32 12C18 12 6 32 6 32C6 32 18 52 32 52C46 52 58 32 58 32C58 32 46 12 32 12Z" stroke={color} strokeWidth="3" />
      
      {/* Tech Pupil */}
      <rect x="26" y="26" width="12" height="12" rx="3" fill={darkMode ? '#0f172a' : '#fff'} stroke={color} strokeWidth="2.5" />
      <circle cx="32" cy="32" r="2.5" fill={color} />
    </svg>
  );

  // 5. VARIATION: The Aperture
  // Concept: A mechanical eye where the iris is segmented like the bridge's stones
  const BifrostAperture = ({ size = 48, color = colors.accent }) => (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
      {/* Outer Eye */}
      <path d="M32 10C16 10 4 32 4 32C4 32 16 54 32 54C48 54 60 32 60 32C60 32 48 10 32 10Z" stroke={color} strokeWidth="2" opacity="0.5" />
      
      {/* Segmented Iris (The Bridge Structure) */}
      <path d="M32 18V24" stroke={color} strokeWidth="3" strokeLinecap="round" />
      <path d="M32 40V46" stroke={color} strokeWidth="3" strokeLinecap="round" />
      <path d="M42 22L38 27" stroke={color} strokeWidth="3" strokeLinecap="round" />
      <path d="M22 22L26 27" stroke={color} strokeWidth="3" strokeLinecap="round" />
      <path d="M42 42L38 37" stroke={color} strokeWidth="3" strokeLinecap="round" />
      <path d="M22 42L26 37" stroke={color} strokeWidth="3" strokeLinecap="round" />

      {/* Center Pupil */}
      <circle cx="32" cy="32" r="4" fill={color} />
    </svg>
  );

  const logos = [
    { component: OriginalEye, name: 'Original', desc: 'The All-Seeing Eye' },
    { component: BifrostBeam, name: 'Bifrost Beam', desc: 'Connecting to the cloud' },
    { component: BifrostArc, name: 'Bifrost Arc', desc: 'Protective oversight' },
    { component: BifrostFlow, name: 'Data Flow', desc: 'High-speed monitoring' },
    { component: BifrostAperture, name: 'The Aperture', desc: 'Structural precision' },
  ];

  const LogoComponent = logos[activeLogo].component;

  return (
    <div className={`min-h-screen p-8 transition-colors duration-300 ${darkMode ? 'bg-slate-950' : 'bg-slate-100'}`}>
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-12">
          <div>
            <h1 className={`text-2xl font-bold ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>
              Heimr.ai - Bifrost Variations
            </h1>
            <p className="text-sky-400 mt-1">Based on the "All-Seeing Eye"</p>
          </div>
          <button
            onClick={() => setDarkMode(!darkMode)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              darkMode ? 'bg-slate-800 text-slate-300' : 'bg-white text-slate-700 shadow'
            }`}
          >
            {darkMode ? 'Light Mode' : 'Dark Mode'}
          </button>
        </div>

        {/* Hero Display */}
        <div className={`rounded-2xl p-12 mb-8 flex flex-col items-center justify-center min-h-[300px] ${darkMode ? 'bg-slate-900' : 'bg-white shadow-lg'}`}>
          <div className="relative group">
            <div className={`absolute -inset-4 rounded-full blur-xl opacity-20 group-hover:opacity-40 transition-opacity duration-500 bg-sky-500`}></div>
            <LogoComponent size={140} color={colors.accent} />
          </div>
          
          <div className="mt-8 text-center">
            <h2 className={`text-3xl font-bold tracking-tight ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>
              {logos[activeLogo].name}
            </h2>
            <p className={`text-lg mt-2 ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
              {logos[activeLogo].desc}
            </p>
          </div>
        </div>

        {/* Selector Grid */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {logos.map((logo, index) => {
            const Logo = logo.component;
            return (
              <button
                key={index}
                onClick={() => setActiveLogo(index)}
                className={`p-4 rounded-xl transition-all duration-200 flex flex-col items-center gap-3 ${
                  activeLogo === index
                    ? 'bg-sky-500/20 ring-2 ring-sky-400'
                    : darkMode 
                      ? 'bg-slate-900 hover:bg-slate-800' 
                      : 'bg-white hover:bg-slate-50 shadow'
                }`}
              >
                <Logo size={32} color={activeLogo === index ? colors.accent : colors.muted} />
                <span className={`text-xs font-medium ${
                  activeLogo === index 
                    ? 'text-sky-400' 
                    : darkMode ? 'text-slate-500' : 'text-slate-400'
                }`}>
                  {logo.name}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default HelmrBifrostVariations;