import type { SVGProps } from "react";

type Props = SVGProps<SVGSVGElement> & { size?: number };

const base = (size = 18) => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.7,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
});

export const WorkspaceIcon = ({ size, ...rest }: Props) => (
  <svg {...base(size)} {...rest}>
    <rect x="3" y="4" width="18" height="16" rx="2.5" />
    <path d="M3 9h18M8.5 9v11" />
  </svg>
);

export const HistoryIcon = ({ size, ...rest }: Props) => (
  <svg {...base(size)} {...rest}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 7.5V12l3 1.8" />
  </svg>
);

export const SunIcon = ({ size, ...rest }: Props) => (
  <svg {...base(size)} {...rest}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2.8v2M12 19.2v2M2.8 12h2M19.2 12h2M5.5 5.5l1.4 1.4M17.1 17.1l1.4 1.4M18.5 5.5l-1.4 1.4M6.9 17.1l-1.4 1.4" />
  </svg>
);

export const MoonIcon = ({ size, ...rest }: Props) => (
  <svg {...base(size)} {...rest}>
    <path d="M20 13.5A8 8 0 019.4 4a8.2 8.2 0 1010.6 9.5z" />
  </svg>
);

export const SaveIcon = ({ size, ...rest }: Props) => (
  <svg {...base(size)} {...rest}>
    <path d="M5 4h11l3 3v13H5z" />
    <path d="M8.5 4v5h7V4M8.5 20v-6h7v6" />
  </svg>
);

export const CopyIcon = ({ size, ...rest }: Props) => (
  <svg {...base(size)} {...rest}>
    <rect x="9" y="9" width="11" height="11" rx="2" />
    <path d="M6 15H4.5V4.5H15V6" />
  </svg>
);

export const DownloadIcon = ({ size, ...rest }: Props) => (
  <svg {...base(size)} {...rest}>
    <path d="M12 4v11M7.5 11.5L12 16l4.5-4.5M5 20h14" />
  </svg>
);

export const TrashIcon = ({ size, ...rest }: Props) => (
  <svg {...base(size)} {...rest}>
    <path d="M4 7h16M9.5 4h5M6.5 7l1 13h9l1-13M10.5 10.5v7M13.5 10.5v7" />
  </svg>
);

export const PlusIcon = ({ size, ...rest }: Props) => (
  <svg {...base(size)} {...rest}>
    <path d="M12 5v14M5 12h14" />
  </svg>
);

export const ArrowIcon = ({ size, ...rest }: Props) => (
  <svg {...base(size)} {...rest}>
    <path d="M5 12h14M13 6l6 6-6 6" />
  </svg>
);

export const SparkIcon = ({ size, ...rest }: Props) => (
  <svg {...base(size)} {...rest}>
    <path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z" />
    <path d="M18.5 16.5l.7 1.8 1.8.7-1.8.7-.7 1.8-.7-1.8-1.8-.7 1.8-.7z" />
  </svg>
);

export const ImageIcon = ({ size, ...rest }: Props) => (
  <svg {...base(size)} {...rest}>
    <rect x="3.5" y="4.5" width="17" height="15" rx="2.5" />
    <circle cx="9" cy="9.5" r="1.4" />
    <path d="M4.5 16.5l4.6-4.6 3.4 3.4 2.6-2.6 4.4 4.4" />
  </svg>
);

export const RefreshIcon = ({ size, ...rest }: Props) => (
  <svg {...base(size)} {...rest}>
    <path d="M20 11a8 8 0 10-2.6 6M20 5v6h-6" />
  </svg>
);

export const ChevronIcon = ({ size, ...rest }: Props) => (
  <svg {...base(size)} {...rest}>
    <path d="M8 10l4 4 4-4" />
  </svg>
);

export const CloverIcon = () => <svg viewBox="0 0 36 36" fill="currentColor" aria-hidden="true"><path d="M18 1 C13 5 9 9 13 13 C16 16 18 15 18 15 C18 15 20 16 23 13 C27 9 23 5 18 1Z"/><path d="M35 18 C31 13 27 9 23 13 C20 16 21 18 21 18 C21 18 20 20 23 23 C27 27 31 23 35 18Z"/><path d="M18 35 C23 31 27 27 23 23 C20 20 18 21 18 21 C18 21 16 20 13 23 C9 27 13 31 18 35Z"/><path d="M1 18 C5 23 9 27 13 23 C16 20 15 18 15 18 C15 18 16 16 13 13 C9 9 5 13 1 18Z"/></svg>;
