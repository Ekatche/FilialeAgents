"use client";

import Image from "next/image";
import { ReactNode } from "react";

interface PageHeroProps {
    backgroundImage: string;
    title: ReactNode;
    description: string;
    children?: ReactNode;
}

export function PageHero({
    backgroundImage,
    title,
    description,
    children,
}: PageHeroProps) {
    return (
        <div className="w-full bg-white px-6 pb-6 pt-0">
            {/* Hero Container - Dark background with image */}
            <div
                className="w-full relative overflow-hidden rounded-b-[2.5rem] rounded-t-none"
                style={{
                    backgroundColor: 'transparent',
                    height: '600px',
                    display: 'flex',
                    alignItems: 'center',
                }}
            >
                {/* Background Image */}
                <div className="absolute inset-0 z-0 overflow-hidden">
                    <Image
                        src={backgroundImage}
                        alt="Hero Background"
                        fill
                        className="object-cover"
                        style={{
                            objectPosition: 'center 60%',
                            transform: 'scale(1.2)',
                        }}
                        priority
                    />
                    {/* Dark Overlay for readability - gradient uniforme et subtil */}
                    <div className="absolute inset-0 bg-black/40" />
                </div>

                {/* Content Wrapper */}
                <div className="relative z-10 w-full max-w-[95%] mx-auto px-6 grid grid-cols-1 lg:grid-cols-12 gap-12 items-end pb-16">
                    {/* Left Column: Title */}
                    <div className="lg:col-span-7 text-left">
                        <h1
                            style={{
                                color: 'rgb(255, 255, 255)',
                                fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
                                fontSize: '64px',
                                fontWeight: 600,
                                lineHeight: '1.1',
                                letterSpacing: '-0.03em',
                                textShadow: '0 2px 20px rgba(0, 0, 0, 0.8), 0 4px 40px rgba(0, 0, 0, 0.6)',
                            }}
                        >
                            {title}
                        </h1>
                    </div>

                    {/* Right Column: Description + CTA */}
                    <div className="lg:col-span-5 text-left flex flex-col gap-8 items-start justify-end">
                        <p
                            style={{
                                color: 'rgba(255, 255, 255, 0.95)',
                                fontSize: '16px',
                                lineHeight: '1.6',
                                maxWidth: '450px',
                                textShadow: '0 2px 10px rgba(0, 0, 0, 0.7), 0 1px 3px rgba(0, 0, 0, 0.5)',
                            }}
                        >
                            {description}
                        </p>
                        {children}
                    </div>
                </div>
            </div>
        </div>
    );
}
