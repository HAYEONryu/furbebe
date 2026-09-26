import { index, route } from '@react-router/dev/routes';

export default [
  index('routes/home.jsx'),
  route('dogs', 'routes/dogs.jsx'),
  route('dogs/:animalId', 'routes/dog-detail.jsx'),
];
