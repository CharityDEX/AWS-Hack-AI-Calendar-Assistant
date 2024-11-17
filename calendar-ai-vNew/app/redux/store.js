import { configureStore } from '@reduxjs/toolkit';
import { meetingsSlice } from './slices/meetingsSlice';
import { optionsSlice } from './slices/optionsSlice';
import { loadStatusSlice } from './slices/loadStatusSlice';
import { transferResponseSlice } from './slices/transferResponseSlice';

export const store = configureStore({
  reducer: {
    meetings: meetingsSlice.reducer,
    options: optionsSlice.reducer,
    loadStatus: loadStatusSlice.reducer,
    transferResponse: transferResponseSlice.reducer,
  }
})