export function HeroFlow() {
  return <svg className="hero-flow glass-flow" viewBox="0 0 1600 850" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <defs>
      <linearGradient id="glass" x1="0" y1="0" x2=".4" y2="1" gradientUnits="objectBoundingBox">
        <stop stopColor="#b8d2e4" stopOpacity=".08"/><stop offset=".18" stopColor="#fff" stopOpacity=".85"/><stop offset=".24" stopColor="#89a3b7" stopOpacity=".2"/><stop offset=".43" stopColor="#eef8ff" stopOpacity=".6"/><stop offset=".49" stopColor="#fff" stopOpacity=".95"/><stop offset=".54" stopColor="#738797" stopOpacity=".18"/><stop offset=".8" stopColor="#d3e8f5" stopOpacity=".55"/><stop offset="1" stopColor="#fff" stopOpacity=".85"/>
      </linearGradient>
      <linearGradient id="edge"><stop stopColor="#d3eafb" stopOpacity=".05"/><stop offset=".45" stopColor="#ecf8ff" stopOpacity=".8"/><stop offset=".7" stopColor="#fff"/><stop offset="1" stopColor="#afcddd" stopOpacity=".2"/></linearGradient>
      <filter id="glow"><feGaussianBlur stdDeviation="7"/></filter>
      <radialGradient id="shine"><stop stopColor="#fff" stopOpacity=".9"/><stop offset="1" stopColor="#d1e9ff" stopOpacity="0"/></radialGradient>
    </defs>
    <g fill="url(#glass)" stroke="url(#edge)">
      <path d="M650 -120 C1160 70 780 195 1180 270 S1750 50 1760 130 L1740 490 C1320 130 1190 520 1010 280 S1080 80 650 -120Z"/>
      <path d="M-180 650 C220 560 330 980 700 655 S1170 340 1240 330 C1500 260 1460 180 1720 120 L1750 620 C1420 400 1300 710 1100 600 S830 650 700 760 S230 770 -180 800Z"/>
      <path d="M-100 720 C320 910 620 750 900 550 S1390 300 1600 470 L1710 900 C1320 680 1110 900 880 750 S320 900 -100 790Z"/>
    </g>
    {Array.from({length: 42}, (_,i) => <path key={i} d={`M ${-180+i*5} ${655+i*3.7} C 250 ${580+i*6}, 360 ${990-i*2}, 750 ${660-i*2} S ${1140+i*3} ${350+i*1.5}, 1280 ${350+i*3} S 1450 ${150+i*7}, 1730 ${100+i*13}`} fill="none" stroke="url(#edge)" strokeWidth={i%7===0?2.5:.65} opacity={i%7===0?.85:.32}/>)}
    <path d="M-100 811 C480 890 650 745 810 590 S1250 385 1340 383 S1470 230 1700 191" fill="none" stroke="#ff2637" strokeWidth="12" opacity=".45" filter="url(#glow)"/>
    <path d="M-100 811 C480 890 650 745 810 590 S1250 385 1340 383 S1470 230 1700 191" fill="none" stroke="#ff5260" strokeWidth="2" opacity=".85"/>
    <ellipse cx="1230" cy="435" rx="155" ry="85" fill="url(#shine)"/><ellipse cx="920" cy="710" rx="160" ry="100" fill="url(#shine)"/>
  </svg>;
}
