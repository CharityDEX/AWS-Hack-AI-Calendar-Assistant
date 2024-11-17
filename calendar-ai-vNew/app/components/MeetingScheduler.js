import React, { useState } from 'react';
import { useDispatch } from 'react-redux';

import { scheduleMeeting } from '../redux/slices/meetingsSlice.js';
import { openOptions } from '../redux/slices/optionsSlice.js';
import { sendSuggestedTimes } from '../redux/slices/transferResponseSlice.js';

import sendData from '../api/sendData.js';

const MeetingScheduler = () => {
  const [title, setTitle] = useState('');
  const [startDate, setStartDate] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endDate, setEndDate] = useState('');
  const [endTime, setEndTime] = useState('');
  const [duration, setDuration] = useState('');
  const [participants, setParticipants] = useState([]);
  const [currentParticipant, setCurrentParticipant] = useState('');
  const [description, setDescription] = useState('');
  
  const dispatch = useDispatch();

  const handleSubmit = async (e) => {
    e.preventDefault();
    const newMeeting = {
      id: Date.now(),
      title,
      duration,
      participants,
      description,
      status: 'Pending',
      confirmedParticipants: [],      
    }
    dispatch(scheduleMeeting(newMeeting));
    dispatch(openOptions());

    const dataToSendBackend = {
      email_addresses: participants,
      start_datetime: `${startDate} ${startTime}:00`,
      end_datetime: `${endDate} ${endTime}:00`,
      meeting_duration: parseInt(duration),
      description,
      title,
    };
    
    try {
      const response = await sendData(dataToSendBackend);
      dispatch(sendSuggestedTimes(response.suggested_slots));
      console.log('Server Response:', response);
    } catch (error) {
      console.log('Error sending data:', error);
    }

  }
  
  const addParticipant = (e) => {
    e.preventDefault()
    if (currentParticipant && !participants.includes(currentParticipant)) {
      setParticipants([...participants, currentParticipant]);
      setCurrentParticipant('');
    }
  }
  
  const removeParticipant = (email) => {
    setParticipants(participants.filter(p => p !== email));
  }

  return (
    <div className='meeting-card'>
      
      <div className='card-label'>
        <h2 className='card-label-text'>Schedule a Meeting</h2>
      </div>

      <div className='title-container'>
        <label htmlFor='meeting-title'>Meeting Title</label>
        <input 
          id='meeting-title'
          className='meeting-title'
          value={title}
          onChange={e => setTitle(e.target.value)}
          
        />
      </div>

      <div className='start-date-time-container'>
        <div className='start-date-container'>
          <label htmlFor=''>Start Date</label>
          <input 
            id='start-date'
            className='start-date'
            type='date'
            value={startDate}
            onChange={e => setStartDate(e.target.value)}
            
          />
        </div>
        <div className='start-time-container'>
          <label htmlFor=''>Start Time</label>
          <input 
            id='start-time'
            className='start-time'
            type='time'
            value={startTime}
            onChange={e => setStartTime(e.target.value)}
            
          />
        </div>
      </div>

      <div className='end-date-time-container'>
        <div className='end-date-container'>
          <label htmlFor=''>End Date</label>
          <input 
            id='end-date'
            className='end-date'
            type='date'
            value={endDate}
            onChange={e => setEndDate(e.target.value)}
            
          />
        </div>
        <div className='end-time-container'>
          <label htmlFor=''>End Time</label>
          <input 
            id='end-time'
            className='end-time'
            type='time'
            value={endTime}
            onChange={e => setEndTime(e.target.value)}
            
          />
        </div>
      </div>

      <div className='duration-container'>
        <label htmlFor="duration">Duration (minutes)</label>
        <input
          type="number"
          id="duration"
          className='duration'
          value={duration}
          onChange={(e) => setDuration(e.target.value)}
          
        />
      </div>

      <div className='participants-container'>
        <form className='participants-form'>
          <input 
            type='email'
            id='participants'
            className='participants'
            value={currentParticipant}
            onChange={e => setCurrentParticipant(e.target.value)}
            placeholder='Enter email address'
          />
          <button type='submit' onClick={addParticipant}>Add</button>
        </form>
        <div className='display-participants'>
          {participants.map((email) => (
            <div key={email} className='participant-bubble'>
              {email}
              <button onClick={() => removeParticipant(email)}>X</button>
            </div>
          ))}
        </div>
      </div>

      <div className='description-container'>
          <label htmlFor='description'>Meeting Description</label>
          <textarea 
            id='description'
            value={description}
            onChange={e => setDescription(e.target.value)}
            rows={4}
          />
      </div>

      <button onClick={handleSubmit}>Schedule Meeting</button>

    </div>
  );
}

export default MeetingScheduler;