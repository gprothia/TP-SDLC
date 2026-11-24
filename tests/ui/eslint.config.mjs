// TypeScript test style and likely-bug checks (standards/coding.md CODE-8).
import js from '@eslint/js';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['node_modules/**', 'reports/**', 'test-results/**'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    rules: {
      'no-restricted-syntax': [
        'error',
        { selector: "CallExpression[callee.property.name='waitForTimeout']", message: 'No fixed sleeps: wait for something visible instead.' },
      ],
    },
  },
);
