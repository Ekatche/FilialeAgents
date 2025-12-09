import React from 'react';

export function InfoSection() {
    return (
        <section className="py-16 bg-white">
            <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
                <h2 className="text-4xl font-bold text-gray-900 mb-6">
                    How It Works
                </h2>
                <p className="text-lg text-gray-600 mb-8 max-w-3xl mx-auto">
                    Our AI-powered platform analyses any company in seconds, extracting detailed information about subsidiaries, corporate structure, and business relationships.
                </p>
                {/* Placeholder for illustration/image */}
                <div className="w-full h-64 bg-gray-100 rounded-lg flex items-center justify-center">
                    <span className="text-gray-500">[Illustration]</span>
                </div>
            </div>
        </section>
    );
}
