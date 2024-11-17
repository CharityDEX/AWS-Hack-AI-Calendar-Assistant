import React from 'react';
import { useSelector } from 'react-redux';
import ChoiceRender from './ChoiceRender';

const MeetingChoices = () => {
  const times = useSelector((state) => state.transferResponse.response);

  return (
    <div className='option-cards-container'>
      <div className="card-label">
        <h2>Select A Time</h2>
      </div>

      <div className="option-cards">
        {Object.entries(times).map(([key, value]) => (
          <ChoiceRender
            key={key} // Use key for React's reconciliation
            data={{
              date: value[0],
              startTime: value[1],
              endTime: value[2],
            }}
          />
        ))}
      </div>
    </div>
  );
};

export default MeetingChoices;
