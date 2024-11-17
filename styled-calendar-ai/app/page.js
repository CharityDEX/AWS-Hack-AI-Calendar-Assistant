'use client';

import './globalStyles.css';

import { Provider } from 'react-redux';
import { store } from './redux/store';

import Application from './Application.js'

const App = () => {
  return (
    <div className='app-container'>
      <Provider store={store}>
        <Application />
      </Provider>
    </div>
  );
}

export default App;