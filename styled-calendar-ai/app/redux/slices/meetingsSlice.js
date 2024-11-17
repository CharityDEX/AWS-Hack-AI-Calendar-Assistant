import { createSlice } from '@reduxjs/toolkit';

export const meetingsSlice = createSlice({
  name: 'meetings',
  initialState: {
    messageHistory: {}
  },
  reducers: {
    scheduleMeeting: (state, action) => {
      state.messageHistory = action.payload;
    },
    addDateTime: (state, action) => {
      state.messageHistory.startTime = action.payload.startTime;
      state.messageHistory.endTime = action.payload.endTime;
      state.messageHistory.date = action.payload.date;
    }
  },
})

export const { scheduleMeeting, addDateTime } = meetingsSlice.actions;
export default meetingsSlice.reducer;