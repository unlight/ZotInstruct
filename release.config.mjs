import { writerOpts } from 'changelog-sentence-case';

/**
 * @type {import('semantic-release').GlobalConfig}
 */

export default {
  branches: ['master'],
  plugins: [
    [
      '@semantic-release/commit-analyzer',
      {
        preset: 'conventionalcommits',
      },
    ],
    [
      '@semantic-release/release-notes-generator',
      {
        preset: 'conventionalcommits',
        writerOpts,
      },
    ],
    '@semantic-release/changelog',
    [
      '@semantic-release/git',
      {
        assets: ['CHANGELOG.md'],
      },
    ],
    [
      '@semantic-release/github',
      {
        labels: false,
      },
    ],
  ],
};
