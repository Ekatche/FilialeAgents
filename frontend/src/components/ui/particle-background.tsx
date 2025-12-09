'use client';

import { useEffect, useRef } from 'react';

interface ParticleBackgroundProps {
    className?: string;
    style?: React.CSSProperties;
}

export function ParticleBackground({ className, style }: ParticleBackgroundProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Set canvas size
        const resizeCanvas = () => {
            canvas.width = canvas.offsetWidth;
            canvas.height = canvas.offsetHeight;
        };
        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);

        // Particle system
        const particles: Array<{
            x: number;
            y: number;
            vx: number;
            vy: number;
            size: number;
            opacity: number;
            color: string;
        }> = [];

        // Create particles
        for (let i = 0; i < 50; i++) {
            particles.push({
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height,
                vx: (Math.random() - 0.5) * 0.5,
                vy: (Math.random() - 0.5) * 0.5,
                size: Math.random() * 2 + 1,
                opacity: Math.random() * 0.5 + 0.2,
                color: Math.random() > 0.5 ? '#FF7A59' : '#FF4D01',
            });
        }

        // Numbers/text particles
        const numbers: Array<{
            x: number;
            y: number;
            text: string;
            opacity: number;
            size: number;
        }> = [];

        for (let i = 0; i < 15; i++) {
            numbers.push({
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height,
                text: String(Math.floor(Math.random() * 1000)),
                opacity: Math.random() * 0.3 + 0.1,
                size: Math.random() * 8 + 6,
            });
        }

        let animationFrame: number;

        const animate = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // Draw particles
            particles.forEach((particle) => {
                particle.x += particle.vx;
                particle.y += particle.vy;

                // Wrap around edges
                if (particle.x < 0) particle.x = canvas.width;
                if (particle.x > canvas.width) particle.x = 0;
                if (particle.y < 0) particle.y = canvas.height;
                if (particle.y > canvas.height) particle.y = 0;

                ctx.beginPath();
                ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
                ctx.fillStyle = particle.color + Math.floor(particle.opacity * 255).toString(16).padStart(2, '0');
                ctx.fill();
            });

            // Draw connecting lines
            particles.forEach((particle, i) => {
                particles.slice(i + 1).forEach((other) => {
                    const dx = particle.x - other.x;
                    const dy = particle.y - other.y;
                    const distance = Math.sqrt(dx * dx + dy * dy);

                    if (distance < 150) {
                        ctx.beginPath();
                        ctx.moveTo(particle.x, particle.y);
                        ctx.lineTo(other.x, other.y);
                        ctx.strokeStyle = `rgba(255, 122, 89, ${0.1 * (1 - distance / 150)})`;
                        ctx.lineWidth = 0.5;
                        ctx.stroke();
                    }
                });
            });

            // Draw numbers
            ctx.fillStyle = 'rgba(255, 255, 255, 0.1)';
            ctx.font = '10px monospace';
            numbers.forEach((num) => {
                ctx.globalAlpha = num.opacity;
                ctx.fillText(num.text, num.x, num.y);
            });
            ctx.globalAlpha = 1;

            animationFrame = requestAnimationFrame(animate);
        };

        animate();

        return () => {
            window.removeEventListener('resize', resizeCanvas);
            cancelAnimationFrame(animationFrame);
        };
    }, []);

    return (
        <canvas
            ref={canvasRef}
            className={className}
            style={style}
        />
    );
}
