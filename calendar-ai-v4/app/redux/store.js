import { configureStore } from '@reduxjs/toolkit';
import { meetingsSlice } from './slices/meetingsSlice';
import { optionsSlice } from './slices/optionsSlice';
import { loadStatusSlice } from './slices/loadStatusSlice';

export const store = configureStore({
  reducer: {
    meetings: meetingsSlice.reducer,
    options: optionsSlice.reducer,
    loadStatus: loadStatusSlice.reducer,
  }
})