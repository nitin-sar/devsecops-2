const calculateDistance = require('../src/utils/calculateDistance');
const parseStringAsArray = require('../src/utils/parseStringAsArray');

describe('utility functions', () => {
  it('parses a comma-separated technology list', () => {
    expect(parseStringAsArray('Node.js, React , MongoDB')).toEqual(['Node.js', 'React', 'MongoDB']);
  });

  it('calculates zero distance for identical coordinates', () => {
    expect(calculateDistance({ latitude: -23.55, longitude: -46.63 }, { latitude: -23.55, longitude: -46.63 })).toBe(0);
  });
});
