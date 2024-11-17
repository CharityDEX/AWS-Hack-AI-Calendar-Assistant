import Header from './components/Header.js';
import MeetingScheduler from './components/MeetingScheduler.js';
import MeetingChoices from './components/MeetingChoices';
import MeetingStatus from './components/MeetingStatus';

import { useSelector } from 'react-redux';

const Application = () => {
  const statusOpen = useSelector(state => state.loadStatus.load);
  const optionsOpen = useSelector((state) => state.options.isOpen);

  return (
    <div className='component-container'>
      <Header />
      <MeetingScheduler />
      {optionsOpen ? <MeetingChoices /> : ''}
      {statusOpen ? <MeetingStatus /> : ''}
    </div>
  )
}

export default Application;