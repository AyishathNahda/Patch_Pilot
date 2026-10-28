import type { Metadata } from "next";
import { Shell } from "@/components/shell";
import { Workspace } from "@/components/workspace";
import "./globals.css";
export const metadata: Metadata = { title: "PatchPilot — Debug with evidence", description: "A local AI debugging workspace. Reproduce bugs, investigate code, and verify candidate patches with real tests." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><Workspace><Shell>{children}</Shell></Workspace></body></html>;
}
