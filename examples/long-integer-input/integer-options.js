// String tokens group the digits without converting them to a number.
export const integerOptions = {
  mask: '9,99#',
  reversed: true,
  tokens: { 9: { pattern: /[0-9]/, repeated: true } },
};
