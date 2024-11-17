import React from 'react';
import { useSelector } from 'react-redux';

const MeetingStatus = () => {
  const meeting = useSelector(state => state.meetings.messageHistory);
  
  console.log("meeting object", meeting);

  return (
    <div className='status-card-container'>
      <div className='card-label'>
        <h2>Meeting Status</h2>
      </div>

      <div className='meeting-status-container'>
        <h4>Meeting Title: {meeting.title}</h4>
        <p>Date: {meeting.date}</p>
        <p>Time: {meeting.startTime} - {meeting.endTime}</p>
        <p>Duration: {meeting.duration} minutes</p>
        <p>Status: {meeting.status}</p>
        <p>Confirmed: {meeting.confirmedParticipants.length} / {meeting.participants.length}</p>
        <div className="participants-container">
          <strong>Participants:</strong>
          <ul>
            {meeting.participants.map(email => (
              <li key={email}>{email}</li>
            ))}
          </ul>
        </div>
      </div>

    </div>
  );
}

export default MeetingStatus;