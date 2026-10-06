/**
 * Mukta (Latin + Devanagari) and Mukta Vaani (Latin + Gujarati) are one design
 * family from Ek Type, so switching language never changes the look of the app.
 * next/font self-hosts them at build time: build once while online and the
 * fonts work during an offline pitch.
 */
import { Mukta, Mukta_Vaani } from "next/font/google";

export const muktaDevanagari = Mukta({
  subsets: ["latin", "devanagari"],
  weight: ["400", "600", "700"],
  variable: "--font-devanagari",
  display: "swap",
});

export const muktaGujarati = Mukta_Vaani({
  subsets: ["latin", "gujarati"],
  weight: ["400", "600", "700"],
  variable: "--font-gujarati",
  display: "swap",
});
