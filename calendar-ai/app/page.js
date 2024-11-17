'use client';

import { Provider } from 'react-redux';
import { store } from './redux/store';

import { useSelector } from 'react-redux';

import Header from './components/Header.js';
import MeetingScheduler from './components/MeetingScheduler.js';
import MeetingChoices from './components/MeetingChoices';
import MeetingStatus from './components/MeetingStatus';

const App = () => {
  return (
    <div>
      <Provider store={store}>
        <Header />
        <MeetingScheduler />
        <MeetingChoices />
      </Provider>
    </div>
  );
}

export default App;