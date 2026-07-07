/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          teal: '#0E7490',
          blue: '#1B4F72',
          gray: '#6B7280',
          grayLight: '#F3F4F6',
          soc: '#555555',
        },
      },
    },
  },
  plugins: [],
};
