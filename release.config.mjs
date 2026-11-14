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
      },
    ],
    '@semantic-release/changelog',
    [
      '@semantic-release/npm',
      {
        // Nothing is published to npm; the plugin keeps package.json and
        // package-lock.json in sync with the released version.
        npmPublish: false,
      },
    ],
    [
      '@semantic-release/git',
      {
        assets: ['CHANGELOG.md', 'package.json', 'package-lock.json'],
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
